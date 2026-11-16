package com.dualmind.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import kotlinx.coroutines.delay
import kotlinx.coroutines.CancellationException
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) { Surface { DualMindScreen() } } }
    }
}

private class Api(private val server: String, private val token: String) {
    suspend fun request(path: String, method: String = "GET", body: JSONObject? = null): String =
        withContext(Dispatchers.IO) {
            val endpoint = java.net.URI(server)
            require(endpoint.scheme == "https" && !endpoint.host.isNullOrBlank() && endpoint.userInfo == null && endpoint.query == null && endpoint.fragment == null) { "Bitte eine gültige HTTPS-Adresse eingeben" }
            val url = URL(server.trimEnd('/') + path)
            val connection = (url.openConnection() as HttpURLConnection)
            try {
                connection.instanceFollowRedirects = false
                connection.requestMethod = method
                connection.connectTimeout = 15000
                connection.readTimeout = 180000
                connection.setRequestProperty("Authorization", "Bearer $token")
                if (body != null) {
                    connection.doOutput = true
                    connection.setRequestProperty("Content-Type", "application/json")
                    connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
                val status = connection.responseCode
                val content = (if (status in 200..299) connection.inputStream else connection.errorStream)
                    ?.bufferedReader()?.use { it.readText() } ?: ""
                if (status !in 200..299) error("HTTP $status: $content")
                content
            } finally { connection.disconnect() }
        }
}

private data class ChatLine(val role: String, val content: String, val origin: String = "legacy")

@Composable
fun DualMindScreen() {
    val context = LocalContext.current
    val credentials = remember { Credentials(context) }
    val saved = remember { credentials.load() }
    var server by remember { mutableStateOf(saved?.first ?: "") }
    var token by remember { mutableStateOf(saved?.second ?: "") }
    var rememberLogin by remember { mutableStateOf(saved != null) }
    var runId by remember { mutableStateOf("") }
    var approvedTransfer by remember { mutableStateOf(false) }
    var knowledge by remember { mutableStateOf("") }
    var knowledgeMode by remember { mutableStateOf(false) }
    var manageProjects by remember { mutableStateOf(false) }
    var taskMode by remember { mutableStateOf(false) }
    var connected by remember { mutableStateOf(false) }
    var roomName by remember { mutableStateOf("Mein Raum") }
    var selectedRoom by remember { mutableStateOf("") }
    var prompt by remember { mutableStateOf("") }
    var noteKey by remember { mutableStateOf("ziel") }
    var noteValue by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Serveradresse und Zugangstoken eingeben.") }
    var busy by remember { mutableStateOf(false) }
    val rooms = remember { mutableStateListOf<Pair<String,String>>() }
    val lines = remember { mutableStateListOf<ChatLine>() }
    val scope = rememberCoroutineScope()
    val api = remember(server, token) { Api(server.trim(), token.trim()) }

    fun runJob(block: suspend () -> Unit) {
        if (busy) return
        scope.launch {
            busy = true
            try { block() } catch (e: CancellationException) { throw e } catch (e: Exception) { status = e.message ?: "Unknown error" }
            finally { busy = false }
        }
    }
    fun reloadRooms() = runJob {
        val arr = JSONArray(api.request("/rooms"))
        rooms.clear()
        for (i in 0 until arr.length()) {
            val item = arr.getJSONObject(i)
            rooms.add(item.getString("id") to item.getString("name"))
        }
        status = "Räume geladen"
    }
    fun reloadMessages() = runJob {
        if (selectedRoom.isBlank()) return@runJob
        val arr = JSONArray(api.request("/rooms/$selectedRoom/messages?latest=true"))
        lines.clear()
        for (i in 0 until arr.length()) {
            val item = arr.getJSONObject(i)
            lines.add(ChatLine(item.getString("role"),item.getString("content"),item.optString("origin")))
        }
        status = "Chat geladen"
    }

    suspend fun monitorRun(id: String) {
        runId = id
        try {
            while (true) {
                val run = JSONObject(api.request("/runs/$runId"))
                status = "${run.getString("state")} · ${run.getInt("calls")} Modellaufrufe"
                val arr = JSONArray(api.request("/rooms/$selectedRoom/messages?latest=true"))
                lines.clear()
                for (i in 0 until arr.length()) {
                    val item = arr.getJSONObject(i)
                    lines.add(ChatLine(item.getString("role"), item.getString("content"), item.optString("origin")))
                }
                if (run.getString("state") !in listOf("queued", "running")) {
                    status += " " + run.optString("error")
                    break
                }
                delay(2000)
            }
        } finally { runId = "" }
    }


    Column(Modifier.fillMaxSize().safeDrawingPadding().imePadding().widthIn(max = 1000.dp).padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("DualMind", style = MaterialTheme.typography.headlineMedium)
            if (connected) TextButton(enabled = !busy, onClick = { credentials.clear(); token = ""; connected = false; selectedRoom = ""; lines.clear(); rooms.clear() }) { Text("Abmelden") }
        }
        if (!connected) {
            OutlinedTextField(server, { server = it }, label = { Text("HTTPS Server URL") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(token, { token = it }, label = { Text("Server-Zugangstoken") }, visualTransformation = PasswordVisualTransformation(), singleLine = true, modifier = Modifier.fillMaxWidth())
            Row { Checkbox(rememberLogin, { rememberLogin = it }); Text("Anmeldung auf diesem Gerät speichern") }
            Button(enabled = !busy, onClick = {
                runJob {
                    val arr = JSONArray(api.request("/rooms"))
                    rooms.clear()
                    for (i in 0 until arr.length()) {
                        val item = arr.getJSONObject(i)
                        rooms.add(item.getString("id") to item.getString("name"))
                    }
                    if (rememberLogin) credentials.save(server.trim(), token.trim()) else credentials.clear()
                    connected = true
                    status = "Verbunden"
                }
            }) { Text("Verbinden") }
        } else {
            TextButton(enabled = !busy, onClick = { manageProjects = !manageProjects }) { Text(if (manageProjects) "Projektverwaltung schließen" else "Projekte verwalten") }
            if (manageProjects) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(roomName, { roomName = it }, label = { Text("Raumname") }, modifier = Modifier.weight(1f))
                Button(enabled = !busy, onClick = {
                    runJob {
                        val created = JSONObject(api.request("/rooms", "POST", JSONObject().put("name", roomName)))
                        selectedRoom = created.getString("id")
                        rooms.add(0, selectedRoom to created.getString("name"))
                        lines.clear()
                        knowledge = ""
                        manageProjects = false
                        status = "Raum erstellt"
                    }
                }) { Text("+") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(enabled = !busy, onClick = { reloadRooms() }) { Text("Räume laden") }
                Button(enabled = !busy && selectedRoom.isNotEmpty(), onClick = { reloadMessages() }) { Text("Chat laden") }
            }
            }
            LazyColumn(modifier = Modifier.heightIn(max = 70.dp)) {
                items(rooms) { room ->
                    TextButton(enabled = !busy, onClick = { selectedRoom = room.first; knowledge = ""; reloadMessages() }) {
                        Text((if (room.first == selectedRoom) "● " else "") + room.second)
                    }
                }
            }
            Row {
                FilterChip(selected = !knowledgeMode, onClick = { knowledgeMode = false }, label = { Text("Gemeinsamer Chat") })
                Spacer(Modifier.width(8.dp))
                FilterChip(selected = knowledgeMode, onClick = { knowledgeMode = true }, label = { Text("Wissen & Aufgaben") })
            }
            HorizontalDivider()
            if (!knowledgeMode) {
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(lines) { line ->
                    Text(when (line.role) { "openai" -> "OpenAI · Modell-API"; "gemini" -> "Gemini · Modell-API"; else -> if (line.origin == "connected_client") "Verbundener Client" else "Du" }, style = MaterialTheme.typography.labelMedium)
                    Text(line.content, modifier = Modifier.padding(bottom = 12.dp))
                }
            }
            TextButton(enabled = !busy && selectedRoom.isNotBlank(), onClick = { runJob {
                val runs = JSONArray(api.request("/rooms/$selectedRoom/runs"))
                if (runs.length() > 0) monitorRun(runs.getJSONObject(0).getString("id")) else status = "Noch kein Lauf vorhanden"
            } }) { Text("Letzten Lauf laden / fortsetzen") }
            OutlinedTextField(prompt, { prompt = it }, label = { Text("Aufgabe für beide KIs") }, modifier = Modifier.fillMaxWidth(), maxLines = 2)
            Row { Checkbox(approvedTransfer, { approvedTransfer = it }); Text("Aufgabe und freigegebenes Wissen an beide Anbieter senden (API-Kosten)") }
            Button(enabled = !busy && approvedTransfer && selectedRoom.isNotEmpty() && prompt.isNotBlank(), onClick = {
                runJob {
                    val data = JSONObject().put("prompt", prompt).put("allow_provider_transfer", true)
                    val created = JSONObject(api.request("/rooms/$selectedRoom/runs", "POST", data))
                    monitorRun(created.getString("id"))
                }
            }) { Text(if (busy) "Arbeitet…" else "API-Zusammenarbeit starten") }
            if (runId.isNotBlank()) TextButton(onClick = {
                scope.launch {
                    try { api.request("/runs/$runId/cancel", "POST", JSONObject()); status = "Abbruch angefordert" }
                    catch (e: Exception) { status = e.message ?: "Verbindungsfehler" }
                }
            }) { Text("Abbrechen") }
            } else {
            Row { Checkbox(taskMode, { taskMode = it }); Text("Als Aufgabe speichern") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(noteKey, { noteKey = it }, label = { Text("Notizschlüssel") }, modifier = Modifier.weight(1f))
                OutlinedTextField(noteValue, { noteValue = it }, label = { Text("Gemeinsame Notiz") }, modifier = Modifier.weight(2f))
            }
            TextButton(enabled = !busy && selectedRoom.isNotEmpty() && noteKey.isNotBlank(), onClick = {
                runJob {
                    api.request("/rooms/$selectedRoom/records", "POST", JSONObject().put("kind", if (taskMode) "task" else "memory").put("title", noteKey).put("content", noteValue).put("source", "user:android").put("approved", true))
                    status = "Notiz gespeichert"
                }
            }) { Text("Gemeinsam speichern und freigeben") }
            }
        }
        if (connected && selectedRoom.isNotBlank() && knowledgeMode) {
            TextButton(enabled = !busy, onClick = { runJob {
                val arr = JSONArray(api.request("/rooms/$selectedRoom/records"))
                knowledge = (0 until arr.length()).joinToString("\n") { i -> val item = arr.getJSONObject(i); "${item.getString("title")}: ${item.getString("content")}" }
            } }) { Text("Gemeinsames Wissen laden") }
            if (knowledge.isNotBlank()) Text(knowledge, modifier = Modifier.weight(1f).verticalScroll(rememberScrollState()))
        }
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        Text(status, style = MaterialTheme.typography.bodySmall)
    }
}
