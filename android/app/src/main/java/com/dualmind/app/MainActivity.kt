package com.dualmind.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
        setContent { MaterialTheme { DualMindScreen() } }
    }
}

private class Api(private val server: String, private val token: String) {
    suspend fun request(path: String, method: String = "GET", body: JSONObject? = null): String =
        withContext(Dispatchers.IO) {
            require(server.startsWith("https://")) { "Use an HTTPS server URL" }
            val url = URL(server.trimEnd('/') + path)
            val connection = (url.openConnection() as HttpURLConnection)
            try {
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

private data class ChatLine(val role: String, val content: String)

@Composable
fun DualMindScreen() {
    var server by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
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
            try { block() } catch (e: Exception) { status = e.message ?: "Unknown error" }
            finally { busy = false }
        }
    }
    fun reloadRooms() = runJob {
        rooms.clear()
        val arr = JSONArray(api.request("/rooms"))
        for (i in 0 until arr.length()) {
            val item = arr.getJSONObject(i)
            rooms.add(item.getString("id") to item.getString("name"))
        }
        status = "Räume geladen"
    }
    fun reloadMessages() = runJob {
        if (selectedRoom.isBlank()) return@runJob
        lines.clear()
        val arr = JSONArray(api.request("/rooms/$selectedRoom/messages"))
        for (i in 0 until arr.length()) {
            val item = arr.getJSONObject(i)
            lines.add(ChatLine(item.getString("role"),item.getString("content")))
        }
        status = "Chat geladen"
    }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        Text("DualMind", style = MaterialTheme.typography.headlineMedium)
        if (!connected) {
            OutlinedTextField(server, { server = it }, label = { Text("HTTPS Server URL") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(token, { token = it }, label = { Text("Server-Zugangstoken") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            Button(enabled = !busy, onClick = {
                runJob {
                    val arr = JSONArray(api.request("/rooms"))
                    rooms.clear()
                    for (i in 0 until arr.length()) {
                        val item = arr.getJSONObject(i)
                        rooms.add(item.getString("id") to item.getString("name"))
                    }
                    connected = true
                    status = "Verbunden"
                }
            }) { Text("Verbinden") }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(roomName, { roomName = it }, label = { Text("Raumname") }, modifier = Modifier.weight(1f))
                Button(enabled = !busy, onClick = {
                    runJob {
                        val created = JSONObject(api.request("/rooms", "POST", JSONObject().put("name", roomName)))
                        selectedRoom = created.getString("id")
                        rooms.add(0, selectedRoom to created.getString("name"))
                        lines.clear()
                        status = "Raum erstellt"
                    }
                }) { Text("+") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(enabled = !busy, onClick = { reloadRooms() }) { Text("Räume laden") }
                Button(enabled = !busy && selectedRoom.isNotEmpty(), onClick = { reloadMessages() }) { Text("Chat laden") }
            }
            LazyColumn(modifier = Modifier.heightIn(max = 110.dp)) {
                items(rooms) { room ->
                    TextButton(onClick = { selectedRoom = room.first; reloadMessages() }) {
                        Text((if (room.first == selectedRoom) "● " else "") + room.second)
                    }
                }
            }
            HorizontalDivider()
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(lines) { line ->
                    Text(line.role.uppercase(), style = MaterialTheme.typography.labelMedium)
                    Text(line.content, modifier = Modifier.padding(bottom = 12.dp))
                }
            }
            OutlinedTextField(prompt, { prompt = it }, label = { Text("Aufgabe für beide KIs") }, modifier = Modifier.fillMaxWidth(), maxLines = 4)
            Button(enabled = !busy && selectedRoom.isNotEmpty() && prompt.isNotBlank(), onClick = {
                runJob {
                    val data = JSONObject().put("prompt", prompt)
                    api.request("/rooms/$selectedRoom/collaborate", "POST", data)
                    prompt = ""
                    lines.clear()
                    val arr = JSONArray(api.request("/rooms/$selectedRoom/messages"))
                    for (i in 0 until arr.length()) {
                        val item = arr.getJSONObject(i)
                        lines.add(ChatLine(item.getString("role"), item.getString("content")))
                    }
                    status = "Diskussionsrunde abgeschlossen"
                }
            }) { Text(if (busy) "Arbeitet…" else "ChatGPT + Gemini diskutieren") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(noteKey, { noteKey = it }, label = { Text("Notizschlüssel") }, modifier = Modifier.weight(1f))
                OutlinedTextField(noteValue, { noteValue = it }, label = { Text("Gemeinsame Notiz") }, modifier = Modifier.weight(2f))
            }
            TextButton(enabled = !busy && selectedRoom.isNotEmpty() && noteKey.isNotBlank(), onClick = {
                runJob {
                    api.request("/rooms/$selectedRoom/notes/${java.net.URLEncoder.encode(noteKey, "UTF-8")}", "PUT", JSONObject().put("value", noteValue))
                    status = "Notiz gespeichert"
                }
            }) { Text("Notiz speichern") }
        }
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        Text(status, style = MaterialTheme.typography.bodySmall)
    }
}
