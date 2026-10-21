using LineupOracle.Ui.Services;

namespace LineupOracle.Ui.Pages;

/// <summary>One ticker entry: a news item, a restart marker, or a restart marker with the item delivered with it.</summary>
public sealed record NewsEntry(long Seq, bool Restarted, string? Text, bool Applied)
{
    public static IReadOnlyList<NewsEntry> From(IReadOnlyList<NewsItemDto> items)
    {
        var entries = new List<NewsEntry>();
        for (var i = 0; i < items.Count; i++)
        {
            var item = items[i];
            if (!item.IsRestart)
            {
                entries.Add(new NewsEntry(item.Seq, false, item.Text, item.Applied));
            }
            else if (i + 1 < items.Count && !items[i + 1].IsRestart)
            {
                entries.Add(new NewsEntry(items[i + 1].Seq, true, items[i + 1].Text, items[i + 1].Applied));
                i++;
            }
            else
            {
                entries.Add(new NewsEntry(item.Seq, true, null, true));
            }
        }

        return entries;
    }
}
