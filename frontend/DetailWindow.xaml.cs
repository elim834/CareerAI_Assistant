using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using frontend.Models;
using frontend.Services;
using System.Diagnostics;

namespace frontend
{
    public partial class DetailWindow : Window
    {
        private readonly ApplicationDto _application;
        private readonly ApiClient _api;
        

        public DetailWindow(ApplicationDto application, AnalysisDto? analysis, ApiClient api)
        {
            InitializeComponent();
            _application = application;
            _api = api;

            TitleText.Text = $"{application.University} — {application.Program}";
            SubRoleTextBox.Text = application.SubRole ?? "";
            OpenListingButton.IsEnabled = !string.IsNullOrWhiteSpace(_application.SourceUrl);

            if (analysis != null)
            {
                ScoreText.Text = $"{analysis.AcceptanceScore}/10";
                ReasoningText.Text = analysis.Reasoning ?? "—";
                LanguageText.Text = FormatLanguageStatus(analysis.LanguageRequirementStatus);
                VisaText.Text = analysis.VisaSummary ?? "—";
                FocusText.Text = analysis.SuggestedFocus ?? "—";
                RisksList.ItemsSource = analysis.Risks ?? new List<string>();
                ActionPlanList.ItemsSource = analysis.ActionPlan ?? new List<string>();
                AnalysisTimestampText.Text = FormatAnalysisTimestamp(analysis.AnalyzedAt);
            }
            else
            {
                ScoreText.Text = application.AcceptanceScore?.ToString() ?? "Not analyzed yet";
                ReasoningText.Text = application.Notes ?? "—";
                LanguageText.Text = "—";
                VisaText.Text = "—";
                FocusText.Text = "—";
                AnalysisTimestampText.Text = "Not analyzed yet";
            }

            DetailsText.Text =
                $"Country: {application.Country}\n" +
                $"Scholarship: {application.ScholarshipAmount}\n" +
                $"Tuition: {application.Tuition}\n" +
                $"TOEFL requirement: {application.ToeflRequirement}\n" +
                $"GPA requirement: {application.GpaRequirement}\n" +
                $"Deadline: {application.Deadline}\n" +
                $"Visa country: {application.VisaCountry}\n" +
                $"Status: {application.Status}";
        }
        
        private void OpenListingButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(_application.SourceUrl)) return;
            Process.Start(new ProcessStartInfo(_application.SourceUrl) { UseShellExecute = true });
        }

        private async void SaveSubRoleButton_Click(object sender, RoutedEventArgs e)
        {
            string newSubRole = SubRoleTextBox.Text.Trim();
            if (string.IsNullOrEmpty(newSubRole)) return;

            await _api.UpdateSubRoleAsync(_application.Id, newSubRole);
            _application.SubRole = newSubRole;
            MessageBox.Show("Saved. Re-run analysis to apply the new sub-role focus.",
                "Saved", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        
        private async void GenerateCoverLetterButton_Click(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            if (button != null) button.IsEnabled = false;

            try
            {
                string autoQuery = $"{_application.University} {_application.Program} research lab";
                var letter = await _api.GenerateCoverLetterAsync(_application.Id, autoQuery);

                if (letter == null)
                {
                    MessageBox.Show("Could not generate the letter. Check backend logs.",
                        "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                string appTitle = $"{_application.University} — {_application.Program}";
                var coverLetterWindow = new CoverLetterWindow(appTitle, letter) { Owner = this };
                coverLetterWindow.ShowDialog();
            }
            finally
            {
                if (button != null) button.IsEnabled = true;
            }
        }        
        public bool WasDeleted { get; private set; } = false;
        
        private string FormatLanguageStatus(string? status)
        {
            return status?.ToLowerInvariant() switch
            {
                "waived" => "✅ Waived",
                "met" => "✅ Requirement met",
                "not met" => "⚠️ Requirement NOT met",
                "unclear" => "❓ Unclear from listing",
                _ => "—"
            };
        }

        private async void DeleteButton_Click(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show(
                $"Are you sure you want to delete \"{_application.University} — {_application.Program}\"?",
                "Confirm Deletion",
                MessageBoxButton.YesNo,
                MessageBoxImage.Warning);

            if (result != MessageBoxResult.Yes) return;

            var button = sender as Button;
            if (button != null) button.IsEnabled = false;

            var success = await _api.DeleteApplicationAsync(_application.Id);
            if (success)
            {
                WasDeleted = true;
                Close();
            }
            else
            {
                MessageBox.Show("Delete operation failed. Check backend logs.",
                    "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                if (button != null) button.IsEnabled = true;
            }
        }
        
        private string FormatAnalysisTimestamp(string? isoTimestamp)
        {
            if (string.IsNullOrWhiteSpace(isoTimestamp)) return "Not analyzed yet";
            if (DateTime.TryParse(isoTimestamp, out var dt))
                return $"Last analyzed: {dt:dddd, MMMM d, yyyy 'at' HH:mm}";
            return "";
        }
        
        private async void RunNewAnalysisButton_Click(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            if (button != null) button.IsEnabled = false;

            try
            {
                var freshAnalysis = await _api.AnalyzeApplicationAsync(_application.Id);
                if (freshAnalysis == null)
                {
                    MessageBox.Show("Could not produce a new analysis. Check backend logs.",
                        "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                ScoreText.Text = $"{freshAnalysis.AcceptanceScore}/10";
                ReasoningText.Text = freshAnalysis.Reasoning ?? "—";
                LanguageText.Text = FormatLanguageStatus(freshAnalysis.LanguageRequirementStatus);
                VisaText.Text = freshAnalysis.VisaSummary ?? "—";
                FocusText.Text = freshAnalysis.SuggestedFocus ?? "—";
                RisksList.ItemsSource = freshAnalysis.Risks ?? new List<string>();
                ActionPlanList.ItemsSource = freshAnalysis.ActionPlan ?? new List<string>();
                AnalysisTimestampText.Text = $"Last analyzed: {DateTime.Now:dddd, MMMM d, yyyy 'at' HH:mm} (just now)";
            }
            finally
            {
                if (button != null) button.IsEnabled = true;
            }
        }
        
        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}