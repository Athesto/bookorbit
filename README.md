# BookOrbit Control

Panel local con interfaces Tkinter y pywebview para BookOrbit, PostgreSQL, Kokoro, Edge TTS y el worker opcional. Interfaz en español, operaciones en segundo plano y logs en vivo. No incluye tray.

## Uso

Docker Desktop debe estar iniciado. Para desarrollar y construir se requiere uv y Python 3.15 (se puede cambiar el intérprete con BOOKORBIT_PYTHON). Se usan imports `lazy` de Python 3.15.

```bash
./run.sh gui
./run.sh build
./run.sh install
./run.sh start
./run.sh stop
./run.sh restart
./run.sh status
./run.sh logs kokoro
```

La app final está en `dist/BookOrbit Control.app`. Incluye Python, Tk, pywebview, el código, index.html y plantillas de Compose; no necesita uv ni la carpeta fuente para ejecutarse. Docker sigue siendo externo. Build para el sistema y arquitectura actuales; no genera un ejecutable Windows desde macOS. La app tiene firma ad hoc para uso local, no notarización para distribución pública.

## Datos y configuración

Configuración activa: `~/Library/Application Support/BookOrbit Control/runtime/`.

En este equipo se ha conservado la instalación existente: Compose y `.env` copiados en esa carpeta, con rutas absolutas a los libros y datos actuales de `~/tmp/sandbox-docker/bookorbit/`. No se han copiado ni movido bases de datos, no se han reiniciado servicios. No borres esa carpeta de datos. Una migración de almacenamiento debe hacerse por separado, con servicios detenidos y respaldo.

Una instalación nueva crea secretos propios y datos bajo Application Support. La plantilla empaquetada no contiene credenciales personales. El token inicial está en el `.env` privado del runtime. No publiques esa carpeta.

Los puertos, nombres de contenedores y proyecto son los de BookOrbit; no inicies otra instalación a la vez con nombres o puertos iguales.

`Iniciar base` inicia app, postgres y edge-tts. Los servicios con perfil (Kokoro y worker) se inician individualmente. Detener todo incluye todos los perfiles. Cerrar el panel o pausar los logs no detiene contenedores.

El worker necesita token y URL configurados. La app no corrige fallos del TTS; los logs permiten investigarlos. Edge TTS requiere internet y envía el texto a Microsoft.

## Seleccionar interfaz

Tkinter se conserva como opción predeterminada. Ambas interfaces utilizan el mismo
`DockerController` de `core.py`; los servicios y datos existentes no cambian.

```bash
uv python install 3.15
uv sync
./run.sh gui                 # Tkinter
./run.sh gui --ui tkinter
./run.sh gui --ui webview    # pywebview: HTML/CSS/JS sin frameworks
./run.sh gui --ui tkinter --smoke-test
./run.sh gui --ui webview --smoke-test
```

`app.py` selecciona la interfaz con `lazy from ... import ...`: la otra interfaz
no se importa. `panel.py` conserva la presentación Tkinter; `webview_ui.py` expone
un adaptador explícito para `index.html`. `core.py` gestiona acciones en segundo
plano, serializa operaciones y publica eventos para ambas vistas. Cada ventana
consume su propia instancia del controlador. Los logs se limitan en memoria.

El build incluye ambas interfaces y `index.html`. No necesitas reconstruir ni
reinstalar la app anterior para probar desde el código fuente. Una app ya
instalada permanece en su versión anterior hasta construir e instalar otra.

## Windows

Desde PowerShell, con uv instalado:

```powershell
uv sync --locked --group build
uv run python app.py --ui webview
.\build.ps1
& ".\dist\BookOrbit Control\BookOrbit Control.exe" --ui webview
```

Para distribuir Windows, descarga y extrae el ZIP completo: el ejecutable necesita
su carpeta `_internal`. Requiere Docker Desktop con contenedores Linux y WebView2
Runtime para pywebview. Tkinter sigue siendo la interfaz predeterminada. Los datos
se guardan en `%LOCALAPPDATA%\BookOrbit Control`; `.env` se abre con Bloc de notas.
Las rutas de volúmenes Docker deben apuntar a carpetas del equipo Windows.

## CI/CD y versiones

Repositorio local: `~/github.com/Athesto/bookorbit`.
GitHub Actions verifica Ruff, formato y pruebas, y construye en runners Windows y
macOS. Se ejecuta en pushes a `main`, pull requests y manualmente. Cada ejecución
guarda ZIPs por sistema y arquitectura y sus SHA256 como artifacts durante 14 días.

Los tags estables `vX.Y.Z` publican una GitHub Release cuando ambos builds pasan.
El tag debe coincidir exactamente con `[project].version` de `pyproject.toml`.
No se crean tags automáticamente en cada commit. Para lanzar una versión:

```bash
# Cambia primero project.version en pyproject.toml.
uv lock
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
git add pyproject.toml uv.lock
git commit -m "Release 0.1.1"
git push origin main
git tag -a v0.1.1 -m "BookOrbit Control 0.1.1"
git push origin v0.1.1
```

El build local usa el mismo `scripts/build.py` que CI y deja los archivos de
publicación en `release/`. El ZIP de macOS conserva el bundle `.app` mediante
`ditto`; el de Windows incluye la distribución completa `--onedir`.
Las releases no contienen `.env`, entornos virtuales ni datos personales.
Los binarios no llevan firma de distribución/notarización. Las pruebas del CI
no sustituyen las pruebas de interfaz y Docker en el equipo de destino.
