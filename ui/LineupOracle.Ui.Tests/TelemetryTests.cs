using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using OpenTelemetry.Trace;

namespace LineupOracle.Ui.Tests;

public sealed class TelemetryTests
{
    private const string Variable = "APPLICATIONINSIGHTS_CONNECTION_STRING";

    [Fact]
    public async Task PageLoadsAndNoTracerIsRegisteredWhenVariableIsUnset()
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseSetting(Variable, ""));
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/");

        Assert.True(response.IsSuccessStatusCode);
        Assert.Null(factory.Services.GetService<TracerProvider>());
    }

    [Fact]
    public void TracerIsRegisteredWhenVariableIsSet()
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseSetting(Variable, "InstrumentationKey=00000000-0000-0000-0000-000000000000;IngestionEndpoint=https://127.0.0.1:9/"));

        Assert.NotNull(factory.Services.GetService<TracerProvider>());
    }
}
