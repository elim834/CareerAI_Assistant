using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using frontend.Models;
using frontend.Services;

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

            if (analysis != null)
            {
                ScoreText.Text = $"{analysis.AcceptanceScore}/10";
                ReasoningText.Text = analysis.Reasoning ?? "—";
                VisaText.Text = analysis.VisaSummary ?? "—";
                FocusText.Text = analysis.SuggestedFocus ?? "—";
                RisksList.ItemsSource = analysis.Risks ?? new List<string>();
                ActionPlanList.ItemsSource = analysis.ActionPlan ?? new List<string>();
            }
            else
            {
                ScoreText.Text = application.AcceptanceScore?.ToString() ?? "Not analyzed yet";
                ReasoningText.Text = application.Notes ?? "—";
                VisaText.Text = "—";
                FocusText.Text = "—";
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

                string keyPoints = letter.KeyPointsToExpand != null
                    ? string.Join("\n• ", letter.KeyPointsToExpand)
                    : "";

                MessageBox.Show(
                    $"OPENING:\n{letter.OpeningParagraph}\n\n" +
                    $"BODY:\n{letter.BodyParagraph}\n\n" +
                    $"LAB FIT:\n{letter.LabFitParagraph}\n\n" +
                    $"CLOSING:\n{letter.ClosingParagraph}\n\n" +
                    $"YOU SHOULD PERSONALLY ADD:\n• {keyPoints}",
                    "Cover Letter Draft",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
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