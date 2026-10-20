using System.Net;
using System.Text;
using System.Text.Json;
using LineupOracle.Ui.Services;
using Microsoft.Extensions.Logging.Abstractions;

namespace LineupOracle.Ui.Tests;

public sealed class LineupApiClientTests
{
    private const string LineupJson = """
        {
          "match_id": "match-1",
          "club": "Harbor City",
          "formation": "4-3-3",
          "players": [
            {
              "id": "harbor-city-1",
              "name": "Hugo Ash",
              "number": 1,
              "position": "GK",
              "p_start": 0.91,
              "explanation": "Started the last match."
            }
          ],
          "alternatives": {
            "GK": [
              {
                "id": "harbor-city-2",
                "name": "Xena Crest",
                "number": 2,
                "position": "GK",
                "p_start": 0.42,
                "explanation": "Available alternative."
              }
            ]
          },
          "llm_used": false,
          "mode": "analyst",
          "language": "en"
        }
        """;

    [Fact]
    public async Task MatchesAreParsed()
    {
        using var client = CreateClient(_ => Json(HttpStatusCode.OK, """
            [{"match_id":"match-1","matchday":3,"home_club":"Harbor City","away_club":"Northmere"}]
            """));
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.GetMatchesAsync();

        Assert.True(result.IsSuccess);
        Assert.Equal("Harbor City", Assert.Single(result.Value!).HomeClub);
    }

    [Fact]
    public async Task LineupIsParsedIncludingAlternativesAndProvenance()
    {
        using var client = CreateClient(_ => Json(HttpStatusCode.OK, LineupJson));
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.PredictAsync(Request());

        Assert.True(result.IsSuccess);
        Assert.Equal(0.91, Assert.Single(result.Value!.Players).PStart);
        Assert.Equal("Xena Crest", Assert.Single(result.Value.Alternatives["GK"]).Name);
        Assert.False(result.Value.LlmUsed);
    }

    [Fact]
    public async Task ClientUsesConfiguredBaseAddress()
    {
        HttpRequestMessage? request = null;
        using var client = new HttpClient(new StubHandler(message =>
        {
            request = message;
            return Json(HttpStatusCode.OK, """
                [{"match_id":"match-1","matchday":3,"home_club":"Harbor City","away_club":"Northmere"}]
                """);
        }))
        {
            BaseAddress = new Uri("http://localhost:8123/")
        };
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        await api.GetMatchesAsync();

        Assert.Equal("http://localhost:8123/matches", request!.RequestUri!.AbsoluteUri);
    }

    [Fact]
    public async Task ClientSendsSessionModeAndLanguageInRequestBody()
    {
        string? body = null;
        using var client = CreateAsyncClient(async request =>
        {
            body = await request.Content!.ReadAsStringAsync();
            return Json(HttpStatusCode.OK, LineupJson);
        });
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        await api.PredictAsync(Request());

        using var json = JsonDocument.Parse(body!);
        Assert.Equal("session-abc", json.RootElement.GetProperty("session_id").GetString());
        Assert.Equal("analyst", json.RootElement.GetProperty("mode").GetString());
        Assert.Equal("es", json.RootElement.GetProperty("language").GetString());
    }

    [Fact]
    public async Task FourHundredStatusReturnsApiDetail()
    {
        using var client = CreateClient(_ => Json(HttpStatusCode.UnprocessableEntity, """{"detail":"Free text is not available yet."}"""));
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.SubmitTeamNewsAsync(new TeamNewsRequest(
            "match-1", "Harbor City", "fan", "zh-Hant", "session-abc", Text: "synthetic player is injured"));

        Assert.False(result.IsSuccess);
        Assert.False(result.IsUnavailable);
        Assert.Equal("Free text is not available yet.", result.Error);
    }

    [Fact]
    public async Task NetworkFailureReturnsUnavailable()
    {
        using var client = CreateClient(_ => throw new HttpRequestException("Connection refused."));
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.GetMatchesAsync();

        Assert.True(result.IsUnavailable);
        Assert.Null(result.Value);
    }

    private static PredictionRequest Request() =>
        new("match-1", "Harbor City", "analyst", "es", "session-abc");

    private static HttpClient CreateClient(Func<HttpRequestMessage, HttpResponseMessage> response) =>
        new(new StubHandler(response)) { BaseAddress = new Uri("http://127.0.0.1:8000/") };

    private static HttpClient CreateAsyncClient(Func<HttpRequestMessage, Task<HttpResponseMessage>> response) =>
        new(new StubHandler(response)) { BaseAddress = new Uri("http://127.0.0.1:8000/") };

    private static HttpResponseMessage Json(HttpStatusCode statusCode, string json) =>
        new(statusCode) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    private sealed class StubHandler(Func<HttpRequestMessage, Task<HttpResponseMessage>> response) : HttpMessageHandler
    {
        public StubHandler(Func<HttpRequestMessage, HttpResponseMessage> response)
            : this(request => Task.FromResult(response(request)))
        {
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            response(request);
    }
}
