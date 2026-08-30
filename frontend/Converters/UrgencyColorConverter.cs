using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace frontend.Converters
{
    public class UrgencyColorConverter : IValueConverter
    {
        public object Convert(object? value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is not int daysLeft)
                return Brushes.Transparent;

            if (daysLeft < 0) return new SolidColorBrush(Color.FromRgb(200, 200, 200)); // passed, grey
            if (daysLeft <= 3) return new SolidColorBrush(Color.FromRgb(255, 205, 210));  // red-ish
            if (daysLeft <= 14) return new SolidColorBrush(Color.FromRgb(255, 236, 179)); // yellow-ish
            return new SolidColorBrush(Color.FromRgb(200, 230, 201));                     // green-ish
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}