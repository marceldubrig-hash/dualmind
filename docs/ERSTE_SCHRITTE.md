# DualMind auf deinem Handy einrichten

Die Test-APK enthält die Android-Oberfläche. Sie braucht deinen eigenen laufenden DualMind-Server. Es ist noch kein öffentlicher Server für dich eingerichtet. Ohne Serveradresse und Anmeldung kann die APK noch keine KI-Diskussion starten.

## 1. Server einrichten

Du brauchst einen dauerhaft erreichbaren Computer oder Server mit Python 3.12. Folge den Befehlen in der README. Lege Zugangstoken und Anbieter-API-Schlüssel ausschließlich in der privaten Server-Konfiguration ab. Die Datei darf nicht in GitHub landen. Ein langer zufälliger Zugangstoken ist Pflicht.

Für den Zugriff vom Handy braucht der Server eine echte HTTPS-Adresse. Die Vorlage `deploy/Caddyfile` übernimmt TLS nach Einrichtung einer eigenen Domain. Die internen Ports bleiben nur lokal erreichbar. Die genauen Schritte stehen in `DEPLOYMENT.md`.

## 2. Test-APK installieren

Lade die APK herunter, öffne sie auf dem Fold7 und erlaube bei Bedarf dieser Download-App die Installation unbekannter Apps. Öffne DualMind, gib deine HTTPS-Serveradresse und den Server-Zugangstoken ein und tippe auf „Verbinden“.

„Anmeldung auf diesem Gerät speichern“ ist freiwillig. Der Zugang wird mit einem gerätegebundenen Android-Keystore-Schlüssel verschlüsselt gespeichert. Anbieter-API-Schlüssel gehören niemals in die Android-App. Die APK ist eine Debug-Testversion; spätere Builds mit anderer Signatur können eine Neuinstallation erfordern. Die gemeinsamen Projektdaten liegen auf dem Server.

## 3. Gemeinsam arbeiten

- Unter „Projekte verwalten“ einen Raum erstellen und auswählen.
- Unter „Wissen & Aufgaben“ ausschließlich die Informationen speichern, die du ausdrücklich freigeben möchtest. Aufgaben lassen sich dort ebenfalls anlegen.
- Im gemeinsamen Chat eine Aufgabe eingeben. Für automatische Zusammenarbeit musst du der Übertragung an beide Modellanbieter und möglichen API-Kosten zustimmen.
- Der Verlauf zeigt OpenAI- und Gemini-Antworten jeweils als Modell-API. Nachrichten über einen verbundenen Client tragen eine andere Herkunft.
- „Abbrechen“ beendet weitere Runden. Eine bereits laufende Anbieter-Anfrage lässt sich nicht zurückholen.
- Nach Verbindungsproblemen „Letzten Lauf laden / fortsetzen“ wählen. Das liest den vorhandenen Lauf weiter und startet keine zusätzlichen Modellaufrufe. Nach einem Server-Neustart werden unterbrochene Läufe nicht automatisch erneut berechnet.

Die Android-App hält letzte geladene Nachrichten im Arbeitsspeicher. Es gibt noch keinen dauerhaften Offline-Cache. Auf dem echten Fold7 wurden bisher keine Geräte- oder Offline-Tests durchgeführt.

## 4. Normales ChatGPT und Gemini anbinden

Dafür muss zusätzlich der OAuth-geschützte MCP-Server öffentlich über HTTPS laufen. Du brauchst einen passend eingerichteten Anmeldedienst mit getrennten Lese- und Schreibrechten. Die Einrichtung steht in `CONNECTORS.md`.

Die bestehende ChatGPT-App und Gemini-App werden dadurch nicht ersetzt. Sie können, soweit im jeweiligen Konto verfügbar, denselben gemeinsamen Arbeitsraum über Werkzeuge lesen und beschreiben. Sie erhalten dadurch keinen automatischen Zugriff auf alte private Chats und werden nicht gegenseitig im Hintergrund geweckt.

Für Deutschland ist Googles dokumentierter Weg über benutzerdefinierte Gemini-Apps derzeit regional eingeschränkt. Android AppFunctions sind noch nicht implementiert; dafür sind außerdem neue Android-Build-Werkzeuge und Google-Preview-/Console-Zugänge nötig. Die Modell-API-Zusammenarbeit ist der separat gekennzeichnete alternative Zugang.

## Noch offen

Öffentliches Hosting, OAuth-Kontoeinrichtung, reale Anbieter-Tests, echte ChatGPT-/Gemini-App-Verbindung und der Test auf deinem Gerät. Die APK allein erledigt diese externen Schritte nicht. Die vollständige Prüfübersicht steht in `STATUS.md`.
