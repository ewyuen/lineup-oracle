using System.Collections.Concurrent;
using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using LineupOracle.Ui;
using LineupOracle.Ui.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Localization;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace LineupOracle.Ui.Tests;

public sealed class LineupUiTests
{
    [Fact]
    public async Task FixtureListAndLineupRenderInFormationTiersWithAlternatives()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();

        var html = await client.GetStringAsync("/");

        Assert.Contains("Matchday 4: Harbor City vs Northmere", html);
        Assert.Contains("Ari Crest", html);
        Assert.Contains("#1", html);
        Assert.Contains("strong passing.", html);
        Assert.Contains("Alternatives", html);
        Assert.Contains("Riley Vale", html);
        Assert.DoesNotContain("player-alt-fwd", ExtractPlayerCards(html));
        AssertOrdered(html, "Forwards", "Midfielders", "Defenders", "Goalkeeper");
        Assert.Equal(11, Regex.Matches(ExtractPlayerCards(html), "class=\"player-card\"").Count);
    }

    [Fact]
    public async Task StaticStylesAndHtmxAssetsAreServed()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();

        using var cssResponse = await client.GetAsync("/css/site.css");
        using var htmxResponse = await client.GetAsync("/js/htmx.min.js");

        Assert.Equal(HttpStatusCode.OK, cssResponse.StatusCode);
        Assert.Contains("--surface:", await cssResponse.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.OK, htmxResponse.StatusCode);
        Assert.Contains("version:\"2.0.8\"", await htmxResponse.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task AnalystShowsEveryProbabilityWhileFanHidesNumbersAndBadgeWithoutChangingXi()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();

        var analystHtml = await client.GetStringAsync("/");
        var analystPlayers = PlayerIds(analystHtml);
        var analystCards = Regex.Matches(
            ExtractPlayerCards(analystHtml),
            "<article class=\"player-card\".*?</article>",
            RegexOptions.Singleline);
        Assert.Equal(11, analystCards.Count);
        Assert.All(analystCards.Cast<Match>(), card =>
            Assert.Matches("P\\(start\\)\\s+\\d+%", card.Value));
        Assert.Contains("Template", analystHtml);

        var fanHtml = await client.GetStringAsync("/?mode=fan");

        Assert.Equal(analystPlayers, PlayerIds(fanHtml));
        Assert.DoesNotContain("P(start)", fanHtml);
        Assert.DoesNotContain("class=\"provenance-badge", fanHtml);
        Assert.Contains("started 3 of the last 5", fanHtml);
        Assert.Contains("mode\":\"fan\"", handler.Calls.Last(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal)).Body);
    }

    [Fact]
    public async Task InjuryPostReturnsOnlyUpdatedLineupAndKeepsOtherPageContentOutOfSwap()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var token = await GetAntiforgeryTokenAsync(client);
        using var request = HtmxPost("/?handler=News", Form(token,
            ("matchId", "match-1"),
            ("club", "Harbor City"),
            ("mode", "analyst"),
            ("playerId", "player-1"),
            ("playerName", "Ari Crest"),
            ("kind", "injury")));

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("#lineup", response.Headers.GetValues("HX-Retarget").Single());
        Assert.Contains("id=\"lineup\"", html);
        Assert.Contains("player-replacement", html);
        Assert.DoesNotContain("data-player-id=\"player-1\"", html);
        Assert.Contains("Ari Crest marked injured; XI updated", html);
        Assert.DoesNotContain("fixture-panel", html);

        var call = handler.Calls.Last(item => item.Path.EndsWith("/team_news", StringComparison.Ordinal));
        using var body = JsonDocument.Parse(call.Body);
        Assert.Equal("analyst", body.RootElement.GetProperty("mode").GetString());
        Assert.Equal("en", body.RootElement.GetProperty("language").GetString());
        Assert.False(string.IsNullOrWhiteSpace(body.RootElement.GetProperty("session_id").GetString()));
    }

    [Fact]
    public async Task HtmxLineupHandlerReturnsOnlyLineupFragment()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        using var request = new HttpRequestMessage(HttpMethod.Get, "/?handler=Lineup&matchId=match-1&club=Harbor%20City&mode=analyst");
        request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Contains("id=\"lineup\"", html);
        Assert.DoesNotContain("<html", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("fixture-panel", html);
    }

    [Fact]
    public async Task ApiDownShowsBannerAndDoesNotReturnOrReplaceLastLineup()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var initial = await client.GetStringAsync("/");
        Assert.Contains("data-player-id=\"player-1\"", initial);
        var token = ExtractAntiforgeryToken(initial);
        handler.FailTeamNews = true;
        using var request = HtmxPost("/?handler=News", Form(token,
            ("matchId", "match-1"),
            ("club", "Harbor City"),
            ("mode", "analyst"),
            ("playerId", "player-1"),
            ("playerName", "Ari Crest"),
            ("kind", "injury")));

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Equal("#news-message", response.Headers.GetValues("HX-Retarget").Single());
        Assert.Contains("Service unavailable", html);
        Assert.Contains("hx-swap-oob=\"outerHTML\"", html);
        Assert.DoesNotContain("id=\"lineup\"", html);
        Assert.DoesNotContain("player-replacement", html);
    }

    [Fact]
    public async Task RetryReloadsLineupAndClearsUnavailableBanner()
    {
        using var handler = new StubApiHandler { FailAll = true };
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var initial = await client.GetStringAsync("/");
        Assert.Contains("Service unavailable", initial);

        handler.FailAll = false;
        using var request = new HttpRequestMessage(HttpMethod.Get, "/?handler=Lineup&matchId=match-1&club=Harbor%20City&mode=analyst");
        request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Contains("id=\"lineup\"", html);
        Assert.Contains("hx-swap-oob=\"outerHTML\"", html);
        Assert.DoesNotContain("Service unavailable", html);
    }

    [Fact]
    public async Task Api422ShowsDetailWithoutReturningLineupFragment()
    {
        using var handler = new StubApiHandler { NewsStatusCode = HttpStatusCode.UnprocessableEntity };
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var token = await GetAntiforgeryTokenAsync(client);
        using var request = HtmxPost("/?handler=News", Form(token,
            ("matchId", "match-1"),
            ("club", "Harbor City"),
            ("mode", "analyst"),
            ("newsText", "Ari Crest is unavailable")));

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Equal("#news-message", response.Headers.GetValues("HX-Retarget").Single());
        Assert.Contains("Free-text team news parsing is not available yet", html);
        Assert.DoesNotContain("id=\"lineup\"", html);
    }

    [Fact]
    public async Task PageUsesConfiguredApiAddressAndContainsNoImagesOrInventedMetrics()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler, "http://lineup.stub:8123/");
        using var client = factory.CreateClient();

        var html = await client.GetStringAsync("/");

        Assert.All(handler.Calls, call => Assert.StartsWith("http://lineup.stub:8123/", call.Uri));
        Assert.DoesNotMatch(new Regex("<img\\b", RegexOptions.IgnoreCase), html);
        Assert.DoesNotContain("confidence", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("latency", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("win probability", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("kickoff", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("venue", html, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task FirstVisitsGetDifferentSessionIdsAndLaterCallsReuseEachId()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var firstBrowser = factory.CreateClient();
        using var secondBrowser = factory.CreateClient();
        var firstPage = await firstBrowser.GetStringAsync("/");
        var secondPage = await secondBrowser.GetStringAsync("/");

        Assert.Contains("id=\"lineup\"", firstPage);
        Assert.Contains("id=\"lineup\"", secondPage);
        var firstPrediction = handler.Calls.Where(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal)).ElementAt(0);
        var secondPrediction = handler.Calls.Where(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal)).ElementAt(1);
        var firstSession = JsonDocument.Parse(firstPrediction.Body).RootElement.GetProperty("session_id").GetString();
        var secondSession = JsonDocument.Parse(secondPrediction.Body).RootElement.GetProperty("session_id").GetString();
        Assert.NotEqual(firstSession, secondSession);

        var token = ExtractAntiforgeryToken(firstPage);
        using var request = HtmxPost("/?handler=News", Form(token,
            ("matchId", "match-1"),
            ("club", "Harbor City"),
            ("mode", "analyst"),
            ("playerId", "player-1"),
            ("playerName", "Ari Crest"),
            ("kind", "doubt")));
        using var response = await firstBrowser.SendAsync(request);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var firstNews = handler.Calls.Last(call => call.Path.EndsWith("/team_news", StringComparison.Ordinal));
        var firstNewsSession = JsonDocument.Parse(firstNews.Body).RootElement.GetProperty("session_id").GetString();
        Assert.Equal(firstSession, firstNewsSession);
    }

    [Theory]
    [InlineData("es", "Delanteros")]
    [InlineData("zh-Hant", "前鋒")]
    public async Task LanguageSelectionSurvivesReload(string language, string expectedLabel)
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var token = await GetAntiforgeryTokenAsync(client);
        using var request = new HttpRequestMessage(HttpMethod.Post, "/?handler=Language")
        {
            Content = Form(token,
                ("language", language),
                ("matchId", "match-1"),
                ("club", "Harbor City"),
                ("mode", "analyst"))
        };

        using var response = await client.SendAsync(request);
        var html = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var renderedTierHeadings = string.Join(", ", Regex.Matches(html, "<h2 class=\"tier-heading\">(.*?)</h2>")
            .Select(match => match.Groups[1].Value));
        Assert.True(WebUtility.HtmlDecode(html).Contains(expectedLabel, StringComparison.Ordinal), $"Rendered tier headings: {renderedTierHeadings}");
        Assert.Contains(language == "es" ? "Idioma" : "語言", WebUtility.HtmlDecode(html));
        var prediction = handler.Calls.Last(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal));
        Assert.Equal(language, JsonDocument.Parse(prediction.Body).RootElement.GetProperty("language").GetString());
    }

    [Fact]
    public async Task FavouritePreselectsOnlyWhenTheMatchIncludesThatClub()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var token = await GetAntiforgeryTokenAsync(client);
        using var favoriteRequest = new HttpRequestMessage(HttpMethod.Post, "/?handler=Favourite")
        {
            Content = Form(token,
                ("favouriteClub", "Northmere"),
                ("matchId", "match-1"),
                ("club", "Harbor City"),
                ("mode", "analyst"))
        };
        using var favoriteResponse = await client.SendAsync(favoriteRequest);
        Assert.Equal(HttpStatusCode.OK, favoriteResponse.StatusCode);
        Assert.Contains("Northmere", await favoriteResponse.Content.ReadAsStringAsync());

        await client.GetAsync("/?matchId=match-1");
        await client.GetAsync("/?matchId=match-2");
        var predictions = handler.Calls
            .Where(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal))
            .Select(call => JsonDocument.Parse(call.Body).RootElement.GetProperty("club").GetString())
            .ToArray();

        Assert.Equal("Northmere", predictions[^2]);
        Assert.Equal("Ravenside", predictions[^1]);
    }

    [Fact]
    public async Task ResourceFilesHaveMatchingKeysAndEnglishFallbackIsAvailable()
    {
        var resourcesPath = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "LineupOracle.Ui", "Resources"));
        var baseKeys = ReadResourceKeys(Path.Combine(resourcesPath, "UiText.resx"));
        Assert.Equal(baseKeys, ReadResourceKeys(Path.Combine(resourcesPath, "UiText.en.resx")));
        Assert.Equal(baseKeys, ReadResourceKeys(Path.Combine(resourcesPath, "UiText.es.resx")));
        Assert.Equal(baseKeys, ReadResourceKeys(Path.Combine(resourcesPath, "UiText.zh-Hant.resx")));

        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        var localizer = factory.Services.GetRequiredService<IStringLocalizer<UiText>>();
        var previousCulture = CultureInfo.CurrentUICulture;
        try
        {
            CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo("zh-Hant");
            Assert.Equal("前鋒", localizer["Forwards"].Value);
            CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo("es");
            var missingTranslation = new UiTextLocalizer(new MissingKeyStringLocalizer(localizer, "Forwards"));
            Assert.Equal("Forwards", missingTranslation["Forwards"].Value);
            var missingFormattedTranslation = new UiTextLocalizer(new MissingKeyStringLocalizer(localizer, "Matchday"));
            Assert.Equal("Matchday 4", missingFormattedTranslation["Matchday", 4].Value);
            CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo("fr");
            Assert.Equal("Lineup Oracle", localizer["AppTitle"].Value);
        }
        finally
        {
            CultureInfo.CurrentUICulture = previousCulture;
        }
    }

    [Fact]
    public async Task PreferencesAndFavouriteSurviveTeamNewsUpdates()
    {
        using var handler = new StubApiHandler();
        using var factory = new UiFactory(handler);
        using var client = factory.CreateClient();
        var initialHtml = await client.GetStringAsync("/");
        using var languageRequest = new HttpRequestMessage(HttpMethod.Post, "/?handler=Language")
        {
            Content = Form(ExtractAntiforgeryToken(initialHtml),
                ("language", "es"),
                ("matchId", "match-1"),
                ("club", "Northmere"),
                ("mode", "fan"))
        };
        using var languageResponse = await client.SendAsync(languageRequest);
        var spanishHtml = await languageResponse.Content.ReadAsStringAsync();
        Assert.Contains("Delanteros", WebUtility.HtmlDecode(spanishHtml));

        using var favoriteRequest = new HttpRequestMessage(HttpMethod.Post, "/?handler=Favourite")
        {
            Content = Form(ExtractAntiforgeryToken(spanishHtml),
                ("favouriteClub", "Northmere"),
                ("matchId", "match-1"),
                ("club", "Harbor City"),
                ("mode", "fan"))
        };
        using var favoriteResponse = await client.SendAsync(favoriteRequest);
        var favoriteHtml = await favoriteResponse.Content.ReadAsStringAsync();
        Assert.Contains("★", WebUtility.HtmlDecode(favoriteHtml));

        using var request = HtmxPost("/?handler=News", Form(ExtractAntiforgeryToken(favoriteHtml),
            ("matchId", "match-1"),
            ("club", "Northmere"),
            ("mode", "fan"),
            ("playerId", "player-1"),
            ("playerName", "Ari Crest"),
            ("kind", "doubt")));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var newsCall = handler.Calls.Last(call => call.Path.EndsWith("/team_news", StringComparison.Ordinal));
        using var body = JsonDocument.Parse(newsCall.Body);
        Assert.Equal("fan", body.RootElement.GetProperty("mode").GetString());
        Assert.Equal("es", body.RootElement.GetProperty("language").GetString());
        Assert.True(body.RootElement.TryGetProperty("session_id", out var sessionId));
        Assert.False(string.IsNullOrWhiteSpace(sessionId.GetString()));

        await client.GetAsync("/?matchId=match-1");
        var reloadPrediction = handler.Calls.Last(call => call.Path.EndsWith("/predict_lineup", StringComparison.Ordinal));
        using var reloadBody = JsonDocument.Parse(reloadPrediction.Body);
        Assert.Equal("Northmere", reloadBody.RootElement.GetProperty("club").GetString());
        Assert.Equal("es", reloadBody.RootElement.GetProperty("language").GetString());
    }

    private static async Task<string> GetAntiforgeryTokenAsync(HttpClient client)
    {
        var html = await client.GetStringAsync("/");
        return ExtractAntiforgeryToken(html);
    }

    private static string ExtractAntiforgeryToken(string html)
    {
        var match = Regex.Match(html, "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"");
        Assert.True(match.Success, "The rendered form did not contain an anti-forgery token.");
        return WebUtility.HtmlDecode(match.Groups[1].Value);
    }

    private static FormUrlEncodedContent Form(string token, params (string Key, string Value)[] fields) =>
        new(fields.Append(("__RequestVerificationToken", token))
            .Select(field => new KeyValuePair<string, string>(field.Item1, field.Item2)));

    private static HttpRequestMessage HtmxPost(string uri, HttpContent content)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, uri) { Content = content };
        request.Headers.Add("HX-Request", "true");
        return request;
    }

    private static string ExtractPlayerCards(string html)
    {
        var start = html.IndexOf("<div class=\"tiers\">", StringComparison.Ordinal);
        var end = html.IndexOf("<div id=\"service-banner\"", StringComparison.Ordinal);
        return start >= 0 && end > start ? html[start..end] : html;
    }

    private static string[] PlayerIds(string html) =>
        Regex.Matches(ExtractPlayerCards(html), "data-player-id=\"([^\"]+)\"")
            .Select(match => match.Groups[1].Value)
            .Order(StringComparer.Ordinal)
            .ToArray();

    private static void AssertOrdered(string source, params string[] values)
    {
        var lastIndex = -1;
        foreach (var value in values)
        {
            var currentIndex = source.IndexOf(value, lastIndex + 1, StringComparison.Ordinal);
            Assert.True(currentIndex > lastIndex, $"Expected '{value}' after index {lastIndex}.");
            lastIndex = currentIndex;
        }
    }

    private static HashSet<string> ReadResourceKeys(string path) =>
        XDocument.Load(path).Root!.Elements("data")
            .Select(element => element.Attribute("name")!.Value)
            .ToHashSet(StringComparer.Ordinal);

    private sealed class MissingKeyStringLocalizer(IStringLocalizer inner, string missingKey) : IStringLocalizer
    {
        public LocalizedString this[string name] =>
            name == missingKey ? new LocalizedString(name, name, resourceNotFound: true) : inner[name];

        public LocalizedString this[string name, params object[] arguments] =>
            name == missingKey
                ? new LocalizedString(name, name, resourceNotFound: true)
                : inner[name, arguments];

        public IEnumerable<LocalizedString> GetAllStrings(bool includeParentCultures) =>
            inner.GetAllStrings(includeParentCultures);
    }

    private sealed class UiFactory(StubApiHandler handler, string apiBaseUrl = "http://lineup.stub/") : WebApplicationFactory<Program>
    {
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.ConfigureAppConfiguration((_, configuration) =>
                configuration.AddInMemoryCollection(new Dictionary<string, string?>
                {
                    ["LineupApi:BaseUrl"] = apiBaseUrl
                }));
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<LineupApiClient>();
                services.AddHttpClient<LineupApiClient>()
                    .ConfigurePrimaryHttpMessageHandler(() => handler);
            });
        }
    }

    private sealed record ApiCall(string Method, string Uri, string Path, string Body);

    private sealed class StubApiHandler : HttpMessageHandler
    {
        private static readonly (string Id, string Name, int Number, string Position, double Probability)[] StartingPlayers =
        [
            ("player-1", "Ari Crest", 11, "FWD", 0.92),
            ("player-2", "Mira Wren", 9, "FWD", 0.73),
            ("player-3", "Tobin Vale", 7, "FWD", 0.45),
            ("player-4", "Dax Calder", 8, "MID", 0.88),
            ("player-5", "Micah Thorne", 6, "MID", 0.51),
            ("player-6", "Bram Jensen", 10, "MID", 0.42),
            ("player-7", "Torin Blake", 3, "DEF", 0.84),
            ("player-8", "Henrik Holt", 4, "DEF", 0.96),
            ("player-9", "Soren Rhys", 5, "DEF", 0.81),
            ("player-10", "Callum Gray", 2, "DEF", 0.49),
            ("player-11", "Jonas Miller", 1, "GK", 0.98)
        ];

        public ConcurrentQueue<ApiCall> Calls { get; } = new();
        public bool FailAll { get; set; }
        public bool FailTeamNews { get; set; }
        public HttpStatusCode? NewsStatusCode { get; set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var body = request.Content is null
                ? ""
                : await request.Content.ReadAsStringAsync(cancellationToken);
            Calls.Enqueue(new ApiCall(request.Method.Method, request.RequestUri!.AbsoluteUri, request.RequestUri.AbsolutePath, body));

            if (FailAll || (FailTeamNews && request.RequestUri.AbsolutePath.EndsWith("/team_news", StringComparison.Ordinal)))
            {
                throw new HttpRequestException("The test API is unavailable.");
            }

            if (request.RequestUri.AbsolutePath.EndsWith("/matches", StringComparison.Ordinal))
            {
                return Json(HttpStatusCode.OK, """
                    [
                      {"match_id":"match-1","matchday":4,"home_club":"Harbor City","away_club":"Northmere"},
                      {"match_id":"match-2","matchday":5,"home_club":"Ravenside","away_club":"Summit Vale"}
                    ]
                    """);
            }

            if (request.RequestUri.AbsolutePath.EndsWith("/team_news", StringComparison.Ordinal) && NewsStatusCode is not null)
            {
                return Json(NewsStatusCode.Value, """{"detail":"Free-text team news parsing is not available yet."}""");
            }

            if (request.RequestUri.AbsolutePath.EndsWith("/predict_lineup", StringComparison.Ordinal) ||
                request.RequestUri.AbsolutePath.EndsWith("/team_news", StringComparison.Ordinal))
            {
                using var requestBody = JsonDocument.Parse(body);
                var root = requestBody.RootElement;
                var playerId = root.TryGetProperty("player_id", out var idValue) && idValue.ValueKind == JsonValueKind.String
                    ? idValue.GetString()
                    : null;
                return Json(HttpStatusCode.OK, BuildLineup(
                    root.GetProperty("match_id").GetString()!,
                    root.GetProperty("club").GetString()!,
                    root.GetProperty("mode").GetString()!,
                    root.GetProperty("language").GetString()!,
                    playerId));
            }

            return Json(HttpStatusCode.NotFound, """{"detail":"Unknown endpoint"}""");
        }

        private static string BuildLineup(string matchId, string club, string mode, string language, string? injuredPlayerId)
        {
            var players = StartingPlayers
                .Where(player => player.Id != injuredPlayerId)
                .Select(PlayerRecord)
                .ToList();
            if (injuredPlayerId is not null)
            {
                players.Add(new Dictionary<string, object>
                {
                    ["id"] = "player-replacement",
                    ["name"] = "Riley Vale",
                    ["number"] = 12,
                    ["position"] = "FWD",
                    ["p_start"] = 0.25,
                    ["explanation"] = "Available alternative."
                });
            }

            var alternatives = new Dictionary<string, object>
            {
                ["FWD"] = new[] { Alternative("player-alt-fwd", "Riley Vale", 19, "FWD", 0.34) },
                ["MID"] = new[] { Alternative("player-alt-mid", "Elian Cole", 14, "MID", 0.41) },
                ["DEF"] = Array.Empty<object>(),
                ["GK"] = Array.Empty<object>()
            };
            return JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["match_id"] = matchId,
                ["club"] = club,
                ["formation"] = "4-3-3",
                ["players"] = players,
                ["alternatives"] = alternatives,
                ["llm_used"] = false,
                ["mode"] = mode,
                ["language"] = language
            });
        }

        private static Dictionary<string, object> PlayerRecord((string Id, string Name, int Number, string Position, double Probability) player) =>
            new()
            {
                ["id"] = player.Id,
                ["name"] = player.Name,
                ["number"] = player.Number,
                ["position"] = player.Position,
                ["p_start"] = player.Probability,
                ["explanation"] = $"Likely starter: P(start) {player.Probability:0.00}, started 3 of the last 5, strong passing."
            };

        private static Dictionary<string, object> Alternative(string id, string name, int number, string position, double probability) =>
            new()
            {
                ["id"] = id,
                ["name"] = name,
                ["number"] = number,
                ["position"] = position,
                ["p_start"] = probability,
                ["explanation"] = "Alternative for this position."
            };

        private static HttpResponseMessage Json(HttpStatusCode statusCode, string json) =>
            new(statusCode) { Content = new StringContent(json, Encoding.UTF8, "application/json") };
    }
}
