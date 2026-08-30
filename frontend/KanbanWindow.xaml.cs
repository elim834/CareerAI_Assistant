using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using frontend.Models;
using frontend.Services;

namespace frontend
{
    public partial class KanbanWindow : Window
    {
        private readonly ApiClient _api;
        private List<ApplicationDto> _applications = new();
        private Point _dragStartPoint;

        public KanbanWindow(ApiClient api, List<ApplicationDto> applications)
        {
            InitializeComponent();
            _api = api;
            _applications = applications;
            LoadColumns();
        }

        private void LoadColumns()
        {
            NewList.Items.Clear();
            AppliedList.Items.Clear();
            AcceptedList.Items.Clear();
            RejectedList.Items.Clear();

            foreach (var app in _applications)
            {
                var item = $"{app.University} — {app.Program}";
                switch (app.Status)
                {
                    case "applied": AppliedList.Items.Add(item); break;
                    case "accepted": AcceptedList.Items.Add(item); break;
                    case "rejected": RejectedList.Items.Add(item); break;
                    default: NewList.Items.Add(item); break;
                }
            }
        }

        private void ListBox_PreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            _dragStartPoint = e.GetPosition(null);
        }

        private void ListBox_MouseMove(object sender, MouseEventArgs e)
        {
            if (e.LeftButton != MouseButtonState.Pressed) return;
            if (sender is not ListBox listBox || listBox.SelectedItem == null) return;

            Point currentPosition = e.GetPosition(null);
            if (Math.Abs(currentPosition.X - _dragStartPoint.X) < 5 &&
                Math.Abs(currentPosition.Y - _dragStartPoint.Y) < 5)
                return;

            var draggedText = listBox.SelectedItem.ToString();
            var data = new DataObject();
            data.SetData("DraggedText", draggedText);
            data.SetData("SourceListBox", listBox);

            DragDrop.DoDragDrop(listBox, data, DragDropEffects.Move);
        }

        private void Column_DragEnter(object sender, DragEventArgs e)
        {
            e.Effects = DragDropEffects.Move;
        }

        private async void Column_Drop(object sender, DragEventArgs e)
        {
            if (sender is not ListBox targetList) return;
            if (!e.Data.GetDataPresent("DraggedText")) return;

            var draggedText = e.Data.GetData("DraggedText") as string;
            var sourceList = e.Data.GetData("SourceListBox") as ListBox;
            if (draggedText == null || sourceList == null || sourceList == targetList) return;

            sourceList.Items.Remove(draggedText);
            targetList.Items.Add(draggedText);

            var newStatus = targetList.Tag.ToString();
            var matchedApp = _applications.Find(a => $"{a.University} — {a.Program}" == draggedText);
            if (matchedApp != null && newStatus != null)
            {
                await _api.UpdateStatusAsync(matchedApp.Id, newStatus);
                matchedApp.Status = newStatus;
            }
        }
    }
}