# TabletMonitor — Agente Windows

## Requisitos
- Windows 10/11 (las tablets donde se instala)
- .NET 8 SDK (solo para compilar — en la máquina de desarrollo)
- .NET 8 Runtime (en las tablets — se puede incluir en el ejecutable)
- Ejecutar la instalación como **Administrador**

---

## Compilación

```bash
# Opción A — Ejecutable que requiere .NET instalado en la tablet (más pequeño ~1MB)
dotnet publish -c Release -r win-x64 --no-self-contained -o ./publish

# Opción B — Ejecutable standalone (incluye .NET, ~60MB, no requiere nada instalado)
dotnet publish -c Release -r win-x64 --self-contained true \
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true \
  -o ./publish
```

---

## Configuración antes de instalar

Edita `appsettings.json` y pon la IP o dominio de tu servidor:

```json
{
  "Server": {
    "Url": "http://192.168.1.100:8000"
  }
}
```

---

## Instalación en cada tablet

1. Copia la carpeta `publish/` a la tablet (ej: `C:\TabletMonitor\`)
2. Abre una terminal **como Administrador**
3. Ejecuta:

```cmd
cd C:\TabletMonitor
TabletMonitor.exe install
```

Eso hace todo automáticamente:
- Registra el dispositivo en el servidor
- Instala el servicio de Windows (inicio automático)
- Configura recuperación ante fallos
- Protege el servicio para que usuarios normales no lo puedan detener

---

## Verificar que funciona

```cmd
# Ver estado del servicio
sc query TabletMonitor

# Ver logs en Event Viewer
eventvwr.msc → Registros de Windows → Aplicación → Filtrar por "TabletMonitor"
```

---

## Probar sin instalar (modo consola)

```cmd
TabletMonitor.exe run
```

Útil para ver en tiempo real los logs y verificar que se conecta al servidor.

---

## Desinstalar

```cmd
TabletMonitor.exe uninstall
```

---

## Estructura de archivos en la tablet

```
C:\TabletMonitor\
├── TabletMonitor.exe       ← el agente
└── appsettings.json        ← configuración (URL del servidor)
```

El token de autenticación se guarda en:
```
HKEY_LOCAL_MACHINE\SOFTWARE\TabletMonitor
  ApiToken  = <token único por dispositivo>
  DeviceId  = <UUID del dispositivo en la base de datos>
```