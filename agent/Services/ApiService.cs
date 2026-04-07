using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using TabletMonitor.Models;

namespace TabletMonitor.Services;

/// <summary>
/// Maneja toda la comunicación con el servidor backend.
/// Lee el token del registro de Windows y lo adjunta en cada request.
/// </summary>
public class ApiService
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<ApiService> _logger;
    private readonly IConfiguration _config;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNamingPolicy        = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition      = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
        PropertyNameCaseInsensitive = true,
    };

    public ApiService(IHttpClientFactory httpClientFactory, ILogger<ApiService> logger, IConfiguration config)
    {
        _httpClientFactory = httpClientFactory;
        _logger            = logger;
        _config            = config;
    }

    /// <summary>
    /// Envía heartbeat al servidor. Retorna null si no hay conectividad.
    /// </summary>
    public async Task<HeartbeatResponse?> SendHeartbeatAsync(HeartbeatPayload payload)
    {
        var token = TokenStorage.GetToken();
        if (string.IsNullOrEmpty(token))
        {
            _logger.LogWarning("No hay token guardado — el dispositivo no está registrado");
            return null;
        }

        return await PostAsync<HeartbeatPayload, HeartbeatResponse>("/api/heartbeat", payload, token);
    }

    /// <summary>
    /// Registra el dispositivo en el servidor por primera vez.
    /// </summary>
    public async Task<RegisterResponse?> RegisterAsync(RegisterRequest request)
    {
        return await PostAsync<RegisterRequest, RegisterResponse>("/api/register", request, bearerToken: null);
    }

    // ────────────────────────────────────────────────
    // HTTP helper con reintentos
    // ────────────────────────────────────────────────

    private async Task<TResponse?> PostAsync<TRequest, TResponse>(
        string endpoint,
        TRequest body,
        string? bearerToken)
    {
        const int maxRetries = 3;

        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                var client  = _httpClientFactory.CreateClient("api");
                var json    = JsonSerializer.Serialize(body, _jsonOptions);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                if (!string.IsNullOrEmpty(bearerToken))
                    client.DefaultRequestHeaders.Authorization =
                        new AuthenticationHeaderValue("Bearer", bearerToken);

                var response = await client.PostAsync(endpoint, content);

                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    return JsonSerializer.Deserialize<TResponse>(responseJson, _jsonOptions);
                }

                _logger.LogWarning("Servidor retornó {code} en {ep} (intento {n}/{max})",
                    (int)response.StatusCode, endpoint, attempt, maxRetries);
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning("Sin conexión al servidor (intento {n}/{max}): {msg}",
                    attempt, maxRetries, ex.Message);
            }
            catch (TaskCanceledException)
            {
                _logger.LogWarning("Timeout al contactar el servidor (intento {n}/{max})", attempt, maxRetries);
            }

            if (attempt < maxRetries)
                await Task.Delay(TimeSpan.FromSeconds(attempt * 2)); // backoff: 2s, 4s
        }

        return default;
    }
}