FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY LineupOracle.Ui/ LineupOracle.Ui/
RUN dotnet publish LineupOracle.Ui -c Release -o /out

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_URLS=http://+:8080
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "LineupOracle.Ui.dll"]
