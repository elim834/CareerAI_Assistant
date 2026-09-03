using System.Windows;
using frontend.Models;

namespace frontend
{
    public partial class LastAnalysisWindow : Window
    {
        public bool GoToApplications { get; private set; } = false;

        public LastAnalysisWindow(string appTitle, LastAnalysisResponse? response)
        {
            InitializeComponent();
            TitleText.Text = appTitle;

            if (response == null || !response.Analyzed || response.Analysis == null)
            {
                NoAnalysisText.Visibility = Visibility.Visible;
                AnalysisPanel.Visibility = Visibility.Collapsed;
                TimestampText.Text = "";
                return;
            }

            var analysis = response.Analysis;

            TimestampText.Text = TryFormatTimestamp(analysis.AnalyzedAt);
            ScoreText.Text = analysis.AcceptanceScore != null ? $"{analysis.AcceptanceScore}/10" : "—";
            ReasoningText.Text = analysis.Reasoning ?? "—";
            LanguageText.Text = analysis.LanguageRequirementStatus ?? "—";
            VisaText.Text = analysis.VisaSummary ?? "—";
            FocusText.Text = analysis.SuggestedFocus ?? "—";
            RisksList.ItemsSource = analysis.Risks ?? new List<string>();
            ActionPlanList.ItemsSource = analysis.ActionPlan ?? new List<string>();
        }

        private string TryFormatTimestamp(string? isoTimestamp)
        {
            if (string.IsNullOrWhiteSpace(isoTimestamp)) return "";
            if (DateTime.TryParse(isoTimestamp, out var dt))
                return $"Analyzed on {dt:dddd, MMMM d, yyyy 'at' HH:mm}";
            return "";
        }

        private void GoToApplicationsButton_Click(object sender, RoutedEventArgs e)
        {
            GoToApplications = true;
            Close();
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}