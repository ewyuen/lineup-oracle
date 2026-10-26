using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace LineupOracle.Ui.Services;

public sealed record ApiResult<T>(T? Value, string? Error, bool IsUnavailable = false)
{
    public bool IsSuccess => Value is not null && Error is null;

    public static ApiResult<T> Success(T value) => new(value, null);
    public static ApiResult<T> Failure(string error) => new(default, error);
    public static ApiResult<T> Unavailable() => new(default, null, true);
}

public sealed record MatchDto(
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("matchday")] int Matchday,
    [property: JsonPropertyName("home_club")] string HomeClub,
    [property: JsonPropertyName("away_club")] string AwayClub);

public sealed record PlayerDto(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("number")] int Number,
    [property: JsonPropertyName("position")] string Position,
    [property: JsonPropertyName("p_start")] double PStart,
    [property: JsonPropertyName("explanation")] string Explanation,
    [property: JsonPropertyName("status")] string Status = "available");

public sealed record CandidateDto(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("number")] int Number,
    [property: JsonPropertyName("position")] string Position,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("included")] bool Included);

public sealed record NewsOutcomeDto(
    [property: JsonPropertyName("outcome")] string Outcome,
    [property: JsonPropertyName("club")] string Club,
    [property: JsonPropertyName("player_name")] string? PlayerName,
    [property: JsonPropertyName("kind")] string? Kind);

public sealed record LineupDto(
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("club")] string Club,
    [property: JsonPropertyName("formation")] string Formation,
    [property: JsonPropertyName("players")] IReadOnlyList<PlayerDto> Players,
    [property: JsonPropertyName("alternatives")] IReadOnlyDictionary<string, IReadOnlyList<PlayerDto>> Alternatives,
    [property: JsonPropertyName("llm_used")] bool LlmUsed,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("candidates")] IReadOnlyList<CandidateDto>? Candidates = null,
    [property: JsonPropertyName("news")] NewsOutcomeDto? News = null);

public sealed record PredictionRequest(
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("club")] string Club,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("session_id")] string SessionId);

public sealed record TeamNewsRequest(
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("club")] string Club,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("player_id")] string? PlayerId = null,
    [property: JsonPropertyName("kind")] string? Kind = null,
    [property: JsonPropertyName("text")] string? Text = null);

public sealed record AlternativeRequest(
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("club")] string Club,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("player_id")] string PlayerId,
    [property: JsonPropertyName("included")] bool Included);

public sealed record NewsItemDto(
    [property: JsonPropertyName("seq")] long Seq,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("match_id")] string? MatchId,
    [property: JsonPropertyName("club")] string? Club,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("applied")] bool Applied)
{
    public bool IsRestart => Kind == "restart";
}

public sealed record NewsDto(
    [property: JsonPropertyName("items")] IReadOnlyList<NewsItemDto> Items,
    [property: JsonPropertyName("latest_seq")] long LatestSeq,
    [property: JsonPropertyName("changed")] bool Changed);

public sealed record RestartDto([property: JsonPropertyName("latest_seq")] long LatestSeq);

public sealed record HistoryEventDto(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("match_id")] string MatchId,
    [property: JsonPropertyName("occurred_at")] string OccurredAt,
    [property: JsonPropertyName("payload")] JsonElement? Payload = null)
{
    public string? Text =>
        Payload is { ValueKind: JsonValueKind.Object } p && p.TryGetProperty("text", out var t) && t.ValueKind == JsonValueKind.String
            ? t.GetString()
            : null;
}

public sealed record PlayerHistoryDto(
    [property: JsonPropertyName("events")] IReadOnlyList<HistoryEventDto> Events,
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("llm_used")] bool LlmUsed);

public sealed class LineupApiClient(HttpClient httpClient, ILogger<LineupApiClient> logger)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public Task<ApiResult<IReadOnlyList<MatchDto>>> GetMatchesAsync(CancellationToken cancellationToken = default) =>
        SendAsync<IReadOnlyList<MatchDto>>(new HttpRequestMessage(HttpMethod.Get, "matches"), cancellationToken);

    public Task<ApiResult<LineupDto>> PredictAsync(PredictionRequest request, CancellationToken cancellationToken = default) =>
        SendAsync<LineupDto>(new HttpRequestMessage(HttpMethod.Post, "predict_lineup")
        {
            Content = JsonContent.Create(request, options: JsonOptions)
        }, cancellationToken);

    public Task<ApiResult<LineupDto>> SubmitTeamNewsAsync(TeamNewsRequest request, CancellationToken cancellationToken = default) =>
        SendAsync<LineupDto>(new HttpRequestMessage(HttpMethod.Post, "team_news")
        {
            Content = JsonContent.Create(request, options: JsonOptions)
        }, cancellationToken);

    public Task<ApiResult<LineupDto>> SelectAlternativeAsync(AlternativeRequest request, CancellationToken cancellationToken = default) =>
        SendAsync<LineupDto>(new HttpRequestMessage(HttpMethod.Post, "alternatives")
        {
            Content = JsonContent.Create(request, options: JsonOptions)
        }, cancellationToken);

    public Task<ApiResult<NewsDto>> GetNewsAsync(long? since, string? matchId, string? club, string? language = null, CancellationToken cancellationToken = default)
    {
        var query = new List<string>();
        if (since is not null) query.Add($"since={since}");
        if (!string.IsNullOrWhiteSpace(matchId)) query.Add($"match_id={Uri.EscapeDataString(matchId)}");
        if (!string.IsNullOrWhiteSpace(club)) query.Add($"club={Uri.EscapeDataString(club)}");
        if (!string.IsNullOrWhiteSpace(language)) query.Add($"language={Uri.EscapeDataString(language)}");
        var uri = query.Count == 0 ? "news" : "news?" + string.Join('&', query);
        return SendAsync<NewsDto>(new HttpRequestMessage(HttpMethod.Get, uri), cancellationToken);
    }

    public Task<ApiResult<RestartDto>> RestartFeedAsync(CancellationToken cancellationToken = default) =>
        SendAsync<RestartDto>(new HttpRequestMessage(HttpMethod.Post, "news/restart"), cancellationToken);

    public Task<ApiResult<PlayerHistoryDto>> AskPlayerHistoryAsync(string question, string sessionId, CancellationToken cancellationToken = default) =>
        SendAsync<PlayerHistoryDto>(new HttpRequestMessage(HttpMethod.Post, "player_history")
        {
            Content = JsonContent.Create(new { question, session_id = sessionId }, options: JsonOptions)
        }, cancellationToken);

    private async Task<ApiResult<T>> SendAsync<T>(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        using (request)
        {
            HttpResponseMessage response;
            try
            {
                response = await httpClient.SendAsync(request, cancellationToken);
            }
            catch (HttpRequestException exception)
            {
                logger.LogWarning(exception, "The lineup API could not be reached.");
                return ApiResult<T>.Unavailable();
            }

            using (response)
            {
                if (!response.IsSuccessStatusCode)
                {
                    var body = await response.Content.ReadAsStringAsync(cancellationToken);
                    if ((int)response.StatusCode is >= 400 and < 500)
                    {
                        return ApiResult<T>.Failure(ReadApiError(body) ?? $"The API rejected the request ({(int)response.StatusCode}).");
                    }

                    logger.LogWarning("The lineup API returned HTTP {StatusCode}.", (int)response.StatusCode);
                    return ApiResult<T>.Failure($"The API request failed ({(int)response.StatusCode}).");
                }

                try
                {
                    var value = await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken);
                    return value is null
                        ? ApiResult<T>.Failure("The API returned an empty response.")
                        : ApiResult<T>.Success(value);
                }
                catch (JsonException exception)
                {
                    logger.LogError(exception, "The lineup API returned an invalid response.");
                    return ApiResult<T>.Failure("The API returned an invalid response.");
                }
            }
        }
    }

    private static string? ReadApiError(string body)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            return document.RootElement.TryGetProperty("detail", out var detail) && detail.ValueKind == JsonValueKind.String
                ? detail.GetString()
                : null;
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
