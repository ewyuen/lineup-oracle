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

    private const string NewsJson = """
        {"items":[{"seq":3,"kind":"news","match_id":"match-1","club":"Harbor City","text":"Pia Ash is out.","applied":true},
                  {"seq":4,"kind":"restart","match_id":null,"club":null,"text":"","applied":true}],
         "latest_seq":4,"changed":true}
        """;

    [Fact]
    public async Task NewsIsRequestedWithAndWithoutSince()
    {
        var uris = new List<string>();
        using var client = CreateClient(request =>
        {
            uris.Add(request.RequestUri!.PathAndQuery);
            return Json(HttpStatusCode.OK, NewsJson);
        });
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.GetNewsAsync(2, "match-1", "Harbor City");
        await api.GetNewsAsync(null, null, null);
        await api.GetNewsAsync(2, "match-1", "Harbor City", "zh-Hant");

        Assert.Equal(["/news?since=2&match_id=match-1&club=Harbor%20City", "/news", "/news?since=2&match_id=match-1&club=Harbor%20City&language=zh-Hant"], uris);
        Assert.Equal(4, result.Value!.LatestSeq);
        Assert.True(result.Value.Changed);
        Assert.False(result.Value.Items[0].IsRestart);
        Assert.True(result.Value.Items[1].IsRestart);
    }

    [Fact]
    public async Task NewsAndRestartReportApiFailures()
    {
        using var down = CreateClient(_ => throw new HttpRequestException("refused"));
        using var broken = CreateClient(_ => Json(HttpStatusCode.InternalServerError, "oops"));
        var offline = new LineupApiClient(down, NullLogger<LineupApiClient>.Instance);
        var failing = new LineupApiClient(broken, NullLogger<LineupApiClient>.Instance);

        Assert.True((await offline.GetNewsAsync(1, null, null)).IsUnavailable);
        Assert.True((await offline.RestartFeedAsync()).IsUnavailable);
        Assert.False((await failing.GetNewsAsync(1, null, null)).IsSuccess);
        Assert.False((await failing.RestartFeedAsync()).IsSuccess);
    }

    [Fact]
    public async Task RestartPostsAndReadsTheLatestSequence()
    {
        HttpRequestMessage? sent = null;
        using var client = CreateClient(request =>
        {
            sent = request;
            return Json(HttpStatusCode.OK, """{"latest_seq":7}""");
        });
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.RestartFeedAsync();

        Assert.Equal(HttpMethod.Post, sent!.Method);
        Assert.Equal("/news/restart", sent.RequestUri!.AbsolutePath);
        Assert.Equal(7, result.Value!.LatestSeq);
    }

    [Fact]
    public async Task PlayerHistoryPostsOnlyTheQuestionAndParsesEvents()
    {
        HttpRequestMessage? sent = null;
        string? body = null;
        using var client = CreateClient(request =>
        {
            sent = request;
            body = request.Content!.ReadAsStringAsync().Result;
            return Json(HttpStatusCode.OK, """
                {"filters":{},"events":[
                  {"id":"e1","type":"team_news","match_id":"match-1","club":"Harbor City","occurred_at":"2026-08-13T15:00:00Z","payload":{"text":"Ash is doubtful."}},
                  {"id":"e2","type":"shot","match_id":"match-1","club":"Harbor City","occurred_at":"2026-08-15T15:10:00Z","payload":{}}],
                 "answer":"Two events.","cited_event_ids":["e1"],"llm_used":true}
                """);
        });
        var api = new LineupApiClient(client, NullLogger<LineupApiClient>.Instance);

        var result = await api.AskPlayerHistoryAsync("What happened to Hugo Ash?");

        Assert.Equal("/player_history", sent!.RequestUri!.AbsolutePath);
        Assert.Equal("""{"question":"What happened to Hugo Ash?"}""", body);
        Assert.True(result.Value!.LlmUsed);
        Assert.Equal(2, result.Value.Events.Count);
        Assert.Equal("Ash is doubtful.", result.Value.Events[0].Text);
        Assert.Null(result.Value.Events[1].Text);
    }

    [Fact]
    public async Task PlayerHistoryMapsRejectionAndOutage()
    {
        using var rejected = CreateClient(_ => Json(HttpStatusCode.UnprocessableEntity, """{"detail":"Send explicit filters."}"""));
        using var down = CreateClient(_ => throw new HttpRequestException("refused"));

        var failure = await new LineupApiClient(rejected, NullLogger<LineupApiClient>.Instance).AskPlayerHistoryAsync("q");
        var outage = await new LineupApiClient(down, NullLogger<LineupApiClient>.Instance).AskPlayerHistoryAsync("q");

        Assert.Equal("Send explicit filters.", failure.Error);
        Assert.True(outage.IsUnavailable);
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
