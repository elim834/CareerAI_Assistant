using System.Windows;
using System.Text;
using frontend.Models;

namespace frontend
{
    public partial class CoverLetterWindow : Window
    {
        private readonly CoverLetterDto _letter;
        private readonly string _appTitle;

        public CoverLetterWindow(string appTitle, CoverLetterDto letter)
        {
            InitializeComponent();
            _letter = letter;
            _appTitle = appTitle;

            TitleText.Text = $"Cover Letter Draft — {appTitle}";
            OpeningText.Text = letter.OpeningParagraph ?? "—";
            BodyText.Text = letter.BodyParagraph ?? "—";
            LabFitText.Text = letter.LabFitParagraph ?? "—";
            ClosingText.Text = letter.ClosingParagraph ?? "—";
            KeyPointsList.ItemsSource = letter.KeyPointsToExpand ?? new List<string>();
        }

        private void CopyAllButton_Click(object sender, RoutedEventArgs e)
        {
            var sb = new StringBuilder();
            sb.AppendLine(_letter.OpeningParagraph ?? "");
            sb.AppendLine();
            sb.AppendLine(_letter.BodyParagraph ?? "");
            sb.AppendLine();
            sb.AppendLine(_letter.LabFitParagraph ?? "");
            sb.AppendLine();
            sb.AppendLine(_letter.ClosingParagraph ?? "");

            if (_letter.KeyPointsToExpand is { Count: > 0 })
            {
                sb.AppendLine();
                sb.AppendLine("--- Points to personally expand on ---");
                foreach (var point in _letter.KeyPointsToExpand)
                    sb.AppendLine($"• {point}");
            }

            try
            {
                Clipboard.SetText(sb.ToString());
                MessageBox.Show("Copied to clipboard.", "Copied",
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Could not copy: {ex.Message}", "Error",
                    MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}