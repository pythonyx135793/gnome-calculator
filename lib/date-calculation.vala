/* SPDX-License-Identifier: GPL-3.0-or-later */

public errordomain DateCalculationError
{
    INVALID_DATE,
    INVALID_OFFSET,
    OUT_OF_RANGE
}

/* Civil Gregorian dates, without a time of day or a time zone. */
public class DateCalculation : Object
{
    private static Date parse_date (string input) throws DateCalculationError
    {
        var text = input.strip ();
        if (text.length != 10 || text[4] != '-' || text[7] != '-')
            throw new DateCalculationError.INVALID_DATE (_("Enter a date as YYYY-MM-DD."));

        for (int i = 0; i < text.length; i++)
        {
            if (i != 4 && i != 7 && (text[i] < '0' || text[i] > '9'))
                throw new DateCalculationError.INVALID_DATE (_("Enter a date as YYYY-MM-DD."));
        }

        int year = int.parse (text.substring (0, 4), 10);
        int month = int.parse (text.substring (5, 2), 10);
        int day = int.parse (text.substring (8, 2), 10);
        if (year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31
            || !Date.valid_dmy ((DateDay) day, (DateMonth) month, (DateYear) year))
            throw new DateCalculationError.INVALID_DATE (_("Enter a valid date between 0001-01-01 and 9999-12-31."));

        Date date = Date ();
        date.set_dmy ((DateDay) day, month, (DateYear) year);
        return date;
    }

    public static int64 parse_offset (string input) throws DateCalculationError
    {
        var text = input.strip ();
        int first = text.has_prefix ("+") || text.has_prefix ("-") ? 1 : 0;
        if (text.length <= first)
            throw new DateCalculationError.INVALID_OFFSET (_("Enter a whole number of days."));
        for (int i = first; i < text.length; i++)
        {
            if (text[i] < '0' || text[i] > '9')
                throw new DateCalculationError.INVALID_OFFSET (_("Enter a whole number of days."));
        }
        int64 days;
        if (!int64.try_parse (text, out days, null, 10))
            throw new DateCalculationError.INVALID_OFFSET (_("The number of days is too large."));
        return days;
    }

    public static int days_between (string start, string end) throws DateCalculationError
    {
        Date first = parse_date (start);
        Date last = parse_date (end);
        return (int) ((int64) last.get_julian () - (int64) first.get_julian ());
    }

    private static int leap_days_before (Date date)
    {
        int year = (int) date.get_year ();
        int previous = year - 1;
        int count = previous / 4 - previous / 100 + previous / 400;
        if (date.get_month () > DateMonth.FEBRUARY
            && Date.valid_dmy (29, DateMonth.FEBRUARY, (DateYear) year))
            count++;
        return count;
    }

    /* Count February 29 in [earlier, later). Equal dates have an empty range. */
    public static int leap_days_between (string start, string end) throws DateCalculationError
    {
        Date first = parse_date (start);
        Date last = parse_date (end);
        int count = leap_days_before (last) - leap_days_before (first);
        return count < 0 ? -count : count;
    }

    private static string shift_days (string start, int64 days, bool subtract) throws DateCalculationError
    {
        Date date = parse_date (start);
        Date upper = Date ();
        upper.set_dmy (31, 12, 9999);
        int64 serial = (int64) date.get_julian ();
        int64 maximum = (int64) upper.get_julian ();

        /* Check the offset before adding or negating it, including int64.MIN. */
        bool outside = subtract
            ? days < serial - maximum || days > serial - 1
            : days < 1 - serial || days > maximum - serial;
        if (outside)
            throw new DateCalculationError.OUT_OF_RANGE (_("The result must be between 0001-01-01 and 9999-12-31."));

        Date result = Date ();
        result.set_julian ((uint) (subtract ? serial - days : serial + days));
        return "%04u-%02u-%02u".printf ((uint) result.get_year (),
                                      (uint) result.get_month (),
                                      (uint) result.get_day ());
    }

    public static string add_days (string start, int64 days) throws DateCalculationError
    {
        return shift_days (start, days, false);
    }

    public static string subtract_days (string start, int64 days) throws DateCalculationError
    {
        return shift_days (start, days, true);
    }
}
