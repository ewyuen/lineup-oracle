using System.Text.RegularExpressions;
using LineupOracle.Ui.Services;

namespace LineupOracle.Ui.Pages;

public sealed record PlayerCardViewModel(PlayerDto Player, string MatchId, string Club, string Mode)
{
    private static readonly Regex InlineProbability = new(
        @"\s*P\(start\)\s*:?\s*(?:\d+(?:\.\d+)?|\.\d+)%?,?\s*",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    public string Explanation => Mode == "fan"
        ? InlineProbability.Replace(Player.Explanation, " ").Trim()
        : Player.Explanation;
}
