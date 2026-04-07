using Microsoft.Extensions.Hosting.WindowsServices;
using TabletMonitor.Services;

namespace TabletMonitor;

class Program
{
    static async Task Main(string[] args)
    {
        // Permitir instalar/desinstalar desde línea de comandos:
        //   TabletMonitor.exe install    → instala el servicio
        //   TabletMonitor.exe uninstall  → desinstala el servicio
        //   TabletMonitor.exe run        → corre en consola (para pruebas)
        if (args.Length > 0)
        {
            switch (args[0].ToLower())
            {
                case "install":
                    ServiceInstaller.Install();
                    return;
                case "uninstall":
                    ServiceInstaller.Uninstall();
                    return;
                case "run":
                    // Corre en consola sin instalarse como servicio
                    break;
            }
        }

        var builder = Host.CreateApplicationBuilder(args);

        // Configurar como Windows Service (se queda en background invisible)
        builder.Services.AddWindowsService(options =>
        {
            options.ServiceName = "TabletMonitor";
        });

        // Registrar servicios
        builder.Services.AddHttpClient("api", client =>
        {
            var serverUrl = builder.Configuration["Server:Url"] ?? "http://localhost:8000";
            client.BaseAddress = new Uri(serverUrl);
            client.Timeout = TimeSpan.FromSeconds(15);
        });

        builder.Services.AddSingleton<RegistrationService>();
        builder.Services.AddSingleton<TelemetryService>();
        builder.Services.AddSingleton<ApiService>();
        builder.Services.AddSingleton<CommandExecutor>();
        builder.Services.AddHostedService<Worker>();

        var host = builder.Build();

        // Primer arranque: registrar dispositivo si aún no tiene token
        using (var scope = host.Services.CreateScope())
        {
            var registration = scope.ServiceProvider.GetRequiredService<RegistrationService>();
            await registration.EnsureRegisteredAsync();
        }

        await host.RunAsync();
    }
}