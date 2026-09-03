using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using frontend.Models;
using frontend.Services;

namespace frontend
{
    public partial class DashboardWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();
        private List<ApplicationDto> _applications = new();
        private ProfileDto? _profile;
        private DateTime _displayedMonth = DateTime.Today;

        public DashboardWindow()
        {
            InitializeComponent();
            TodayText.Text = $"Today: {DateTime.Today:dddd, MMMM d, yyyy}";
            Loaded += DashboardWindow_Loaded;
        }

        private async void DashboardWindow_Loaded(object sender, RoutedEventArgs e)
        {
            await LoadDataAsync();
        }

        private async Task LoadDataAsync()
        {
            try
            {
                StatusText.Text = "Loading...";
                _applications = await _api.GetApplicationsAsync();
                _profile = await _api.GetProfileAsync();

                BuildCalendar();
                BuildRecommendations();
                BuildPriorityList();

                StatusText.Text = $"{_applications.Count} application(s) tracked.";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Failed to load dashboard: {ex.Message}";
            }
        }

        // ---------- Calendar ----------

        private void BuildCalendar()
        {
            MonthLabel.Text = _displayedMonth.ToString("MMMM yyyy");
            CalendarGrid.Items.Clear();

            var firstOfMonth = new DateTime(_displayedMonth.Year, _displayedMonth.Month, 1);
            // Monday-first grid: shift so Monday = 0 ... Sunday = 6
            int leadingEmpty = ((int)firstOfMonth.DayOfWeek + 6) % 7;
            var gridStart = firstOfMonth.AddDays(-leadingEmpty);

            // Map deadlines to dates for quick lookup
            var deadlineMap = new Dictionary<DateTime, List<ApplicationDto>>();
            foreach (var app in _applications)
            {
                if (string.IsNullOrWhiteSpace(app.Deadline)) continue;
                if (!DateTime.TryParse(app.Deadline, out var d)) continue;
                var key = d.Date;
                if (!deadlineMap.ContainsKey(key))
                    deadlineMap[key] = new List<ApplicationDto>();
                deadlineMap[key].Add(app);
            }

            for (int i = 0; i < 42; i++) // 6 weeks always shown, keeps layout stable
            {
                var date = gridStart.AddDays(i);
                var cell = new CalendarDayCell
                {
                    Day = date.Day,
                    Date = date,
                    IsCurrentMonth = date.Month == _displayedMonth.Month,
                    IsToday = date.Date == DateTime.Today
                };

                if (deadlineMap.TryGetValue(date.Date, out var apps))
                {
                    cell.DeadlineCount = apps.Count;
                    foreach (var a in apps) cell.DeadlineApps.Add(a);
                }

                CalendarGrid.Items.Add(BuildDayCellVisual(cell));
            }
        }

        private Border BuildDayCellVisual(CalendarDayCell cell)
{
    // Container that lets us layer a colored circle behind the day number.
    var numberContainer = new Grid
    {
        Width = 28,
        Height = 28,
        HorizontalAlignment = HorizontalAlignment.Center
    };

    if (cell.DeadlineCount > 0)
    {
        numberContainer.Children.Add(new Ellipse
        {
            Width = 26,
            Height = 26,
            Fill = GetDeadlineDotColor(cell.Date),
            Opacity = cell.IsCurrentMonth ? 1.0 : 0.4
        });
    }

    numberContainer.Children.Add(new TextBlock
    {
        Text = cell.Day.ToString(),
        HorizontalAlignment = HorizontalAlignment.Center,
        VerticalAlignment = VerticalAlignment.Center,
        FontWeight = (cell.IsToday || cell.DeadlineCount > 0) ? FontWeights.Bold : FontWeights.Normal,
        Foreground = GetDayNumberForeground(cell)
    });

    var stack = new StackPanel { HorizontalAlignment = HorizontalAlignment.Center };
    stack.Children.Add(numberContainer);

    // Small badge for multiple deadlines on the same day, shown below the circle.
    if (cell.DeadlineCount > 1)
    {
        stack.Children.Add(new TextBlock
        {
            Text = $"+{cell.DeadlineCount - 1}",
            HorizontalAlignment = HorizontalAlignment.Center,
            FontSize = 9,
            Foreground = Brushes.Gray,
            Margin = new Thickness(0, 1, 0, 0)
        });
    }

    var border = new Border
    {
        Margin = new Thickness(2),
        Padding = new Thickness(4),
        CornerRadius = new CornerRadius(4),
        Background = cell.IsToday && cell.DeadlineCount == 0
            ? new SolidColorBrush(Color.FromRgb(33, 150, 243))
            : Brushes.Transparent,
        Cursor = System.Windows.Input.Cursors.Hand,
        Tag = cell,
        Child = stack
    };
    border.MouseLeftButtonUp += DayCell_Click;

    return border;
}

        private Brush GetDayNumberForeground(CalendarDayCell cell)
{
    if (!cell.IsCurrentMonth) return Brushes.LightGray;
    if (cell.DeadlineCount > 0) return Brushes.White; // sits on top of the colored circle
    if (cell.IsToday) return Brushes.White; // sits on top of the blue "today" background
    return Brushes.Black;
}
        private Brush GetDeadlineDotColor(DateTime date)
        {
            int daysLeft = (date.Date - DateTime.Today).Days;
            if (daysLeft < 0) return Brushes.Gray;
            if (daysLeft <= 3) return new SolidColorBrush(Color.FromRgb(229, 57, 53));
            if (daysLeft <= 14) return new SolidColorBrush(Color.FromRgb(251, 140, 0));
            return new SolidColorBrush(Color.FromRgb(67, 160, 71));
        }

        private void DayCell_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            if (sender is not Border border || border.Tag is not CalendarDayCell cell) return;

            SelectedDayHeader.Text = cell.Date.ToString("dddd, MMMM d, yyyy");

            if (cell.DeadlineApps.Count == 0)
            {
                SelectedDayList.ItemsSource = new List<string> { "No deadlines on this day." };
            }
            else
            {
                SelectedDayList.ItemsSource = cell.DeadlineApps
                    .Select(a => $"• {a.University} — {a.Program}")
                    .ToList();
            }
        }

        private void PrevMonth_Click(object sender, RoutedEventArgs e)
        {
            _displayedMonth = _displayedMonth.AddMonths(-1);
            BuildCalendar();
        }

        private void NextMonth_Click(object sender, RoutedEventArgs e)
        {
            _displayedMonth = _displayedMonth.AddMonths(1);
            BuildCalendar();
        }

        // ---------- Recommendations ----------

        private void BuildRecommendations()
        {
            var items = new List<RecommendationItem>();
            var active = _applications
                .Where(a => a.Status != "rejected" && a.Status != "accepted")
                .ToList();

            int criticalDeadlines = active.Count(a => a.DaysLeft is >= 0 and <= 3);
            if (criticalDeadlines > 0)
            {
                items.Add(new RecommendationItem
                {
                    Severity = RecommendationSeverity.Critical,
                    Text = $"{criticalDeadlines} application(s) have a deadline within 3 days."
                });
            }

            int soonDeadlines = active.Count(a => a.DaysLeft is > 3 and <= 14);
            if (soonDeadlines > 0)
            {
                items.Add(new RecommendationItem
                {
                    Severity = RecommendationSeverity.Warning,
                    Text = $"{soonDeadlines} application(s) are due within the next two weeks."
                });
            }

            int passedButOpen = active.Count(a => a.DaysLeft is < 0);
            if (passedButOpen > 0)
            {
                items.Add(new RecommendationItem
                {
                    Severity = RecommendationSeverity.Warning,
                    Text = $"{passedButOpen} application(s) have a deadline that already passed but are still marked open. Consider updating their status."
                });
            }

            int unanalyzed = active.Count(a => a.AcceptanceScore == null);
            if (unanalyzed > 0)
            {
                items.Add(new RecommendationItem
                {
                    Severity = RecommendationSeverity.Info,
                    Text = $"{unanalyzed} application(s) haven't been analyzed yet. Run analysis to see your acceptance chances."
                });
            }

            bool needsToefl = active.Any(a => a.ToeflRequirement != null);
            bool hasLanguageScore = _profile is { ToeflScore: not null } or { IeltsScore: not null };
            if (needsToefl && _profile != null && !hasLanguageScore)
            {
                items.Add(new RecommendationItem
                {
                    Severity = RecommendationSeverity.Info,
                    Text = "Some programs require TOEFL/IELTS, but no score is set on your profile. Add one for a more accurate acceptance analysis."
                });
            }

            RecommendationsList.ItemsSource = items;
            NoRecommendationsText.Visibility = items.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        }

        // ---------- Priority list ----------

        private void BuildPriorityList()
        {
            var active = _applications
                .Where(a => a.Status != "rejected" && a.Status != "accepted")
                .ToList();

            var priorityItems = active
                .Select(a => new
                {
                    App = a,
                    // Applications with no deadline sort after those with one.
                    SortDays = a.DaysLeft ?? int.MaxValue,
                    Score = a.AcceptanceScore ?? -1
                })
                .OrderBy(x => x.SortDays)
                .ThenByDescending(x => x.Score)
                .Select(x => new PriorityItem
                {
                    Id = x.App.Id,
                    Title = $"{x.App.University} — {x.App.Program}",
                    DaysLeftDisplay = x.App.DaysLeftDisplay,
                    ScoreDisplay = x.App.AcceptanceScore != null ? $"{x.App.AcceptanceScore}/10" : "—",
                    PriorityLabel = GetPriorityLabel(x.App.DaysLeft),
                    PriorityIcon = GetPriorityIcon(x.App.DaysLeft)
                })
                .ToList();

            PriorityList.ItemsSource = priorityItems;
        }

        private string GetPriorityLabel(int? daysLeft)
        {
            if (daysLeft == null) return "No deadline";
            if (daysLeft < 0) return "Passed";
            if (daysLeft <= 3) return "Critical";
            if (daysLeft <= 14) return "Soon";
            return "Normal";
        }
        private async void PriorityItem_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            if (sender is not Border border || border.DataContext is not PriorityItem item) return;

            var response = await _api.GetLastAnalysisAsync(item.Id);
            var window = new LastAnalysisWindow(item.Title, response) { Owner = this };
            window.ShowDialog();

            if (window.GoToApplications)
            {
                OpenApplicationsButton_Click(sender, e);
            }
        }

        private string GetPriorityIcon(int? daysLeft)
        {
            if (daysLeft == null) return "⚪";
            if (daysLeft < 0) return "⚫";
            if (daysLeft <= 3) return "🔴";
            if (daysLeft <= 14) return "🟡";
            return "🟢";
        }

        // ---------- Navigation ----------

        private void OpenApplicationsButton_Click(object sender, RoutedEventArgs e)
        {
            var mainWindow = new MainWindow();
            mainWindow.Show();
            Close();
        }
    }
}