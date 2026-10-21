using LineupOracle.Ui.Services;
using LineupOracle.Ui;
using System.Globalization;
using Microsoft.AspNetCore.Localization;
using Microsoft.Extensions.Localization;
using Azure.Monitor.OpenTelemetry.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

// Traces go to Application Insights only when the deployment sets the connection string.
if (!string.IsNullOrWhiteSpace(builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"]))
{
    builder.Services.AddOpenTelemetry().UseAzureMonitor();
}

builder.Services.AddLocalization();
builder.Services.AddTransient<IStringLocalizer<UiText>>(services =>
    new UiTextLocalizer(services.GetRequiredService<IStringLocalizerFactory>().Create(typeof(UiText))));
builder.Services.AddRazorPages().AddViewLocalization();
builder.Services.AddHttpClient<LineupApiClient>(client =>
{
    var configuredBaseUrl = builder.Configuration["LineupApi:BaseUrl"];
    var baseUrl = string.IsNullOrWhiteSpace(configuredBaseUrl)
        ? "http://127.0.0.1:8000"
        : configuredBaseUrl;
    if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var baseAddress))
    {
        throw new InvalidOperationException("LineupApi:BaseUrl must be an absolute URL.");
    }

    client.BaseAddress = new Uri(baseAddress.AbsoluteUri.TrimEnd('/') + "/");
});
builder.Services.Configure<RequestLocalizationOptions>(options =>
{
    var supportedCultures = new[] { "en", "es", "zh-Hant" }.Select(CultureInfo.GetCultureInfo).ToList();
    options.DefaultRequestCulture = new RequestCulture("en");
    options.SupportedCultures = supportedCultures;
    options.SupportedUICultures = supportedCultures;
    options.RequestCultureProviders =
    [
        new CookieRequestCultureProvider { CookieName = AppCookies.Language }
    ];
});

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
}

app.UseRequestLocalization();
app.UseRouting();
app.UseAuthorization();
app.MapStaticAssets();
app.MapRazorPages()
   .WithStaticAssets();

app.Run();

public partial class Program
{
}
