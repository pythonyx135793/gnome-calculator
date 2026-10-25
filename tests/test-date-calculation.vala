/* SPDX-License-Identifier: GPL-3.0-or-later */

private void expect_bad_date (string text)
{
    try
    {
        DateCalculation.add_days (text, 0);
        assert_not_reached ();
    }
    catch (DateCalculationError failure)
    {
        assert (failure is DateCalculationError.INVALID_DATE);
    }
}

private void expect_bad_offset (string text)
{
    try
    {
        DateCalculation.parse_offset (text);
        assert_not_reached ();
    }
    catch (DateCalculationError failure)
    {
        assert (failure is DateCalculationError.INVALID_OFFSET);
    }
}

private void expect_outside (string date, int64 days, bool subtract)
{
    try
    {
        if (subtract)
            DateCalculation.subtract_days (date, days);
        else
            DateCalculation.add_days (date, days);
        assert_not_reached ();
    }
    catch (DateCalculationError failure)
    {
        assert (failure is DateCalculationError.OUT_OF_RANGE);
    }
}

private void test_date_validation ()
{
    string[] invalid = { "", "2024-2-29", "2024/02/29", "abcd-02-29", "0000-01-01",
                         "10000-01-01", "2024-00-01", "2024-13-01", "2024-01-00",
                         "2024-01-32", "2024-04-31", "1900-02-29", "2100-02-29",
                         "2023-02-29", "２０２４-02-29", "2024-02-29x" };
    foreach (var text in invalid)
        expect_bad_date (text);
    try
    {
        assert (DateCalculation.add_days (" 2000-02-29 ", 0) == "2000-02-29");
        assert (DateCalculation.add_days ("0001-01-01", 0) == "0001-01-01");
        assert (DateCalculation.add_days ("9999-12-31", 0) == "9999-12-31");
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

private void test_differences ()
{
    try
    {
        assert (DateCalculation.days_between ("2024-02-29", "2024-02-29") == 0);
        assert (DateCalculation.days_between ("2000-02-28", "2000-03-01") == 2);
        assert (DateCalculation.days_between ("1900-02-28", "1900-03-01") == 1);
        assert (DateCalculation.days_between ("2000-03-01", "2000-02-28") == -2);
        assert (DateCalculation.days_between ("1999-12-31", "2000-01-01") == 1);
        assert (DateCalculation.days_between ("1600-01-01", "2000-01-01") == 146097);
        assert (DateCalculation.days_between ("0001-01-01", "9999-12-31") == 3652058);
        assert (DateCalculation.days_between ("2024-03-09", "2024-03-11") == 2);
        assert (DateCalculation.days_between ("2024-11-02", "2024-11-04") == 2);
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

private void test_leap_ranges ()
{
    try
    {
        assert (DateCalculation.leap_days_between ("2000-02-29", "2000-02-29") == 0);
        assert (DateCalculation.leap_days_between ("2000-02-28", "2000-02-29") == 0);
        assert (DateCalculation.leap_days_between ("2000-02-29", "2000-03-01") == 1);
        assert (DateCalculation.leap_days_between ("2000-03-01", "2000-02-29") == 1);
        assert (DateCalculation.leap_days_between ("1900-01-01", "1901-01-01") == 0);
        assert (DateCalculation.leap_days_between ("2000-01-01", "2001-01-01") == 1);
        assert (DateCalculation.leap_days_between ("1600-01-01", "2000-01-01") == 97);
        assert (DateCalculation.leap_days_between ("0001-01-01", "9999-12-31") == 2424);
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

private void test_offsets ()
{
    try
    {
        assert (DateCalculation.add_days ("2000-02-28", 1) == "2000-02-29");
        assert (DateCalculation.add_days ("1900-02-28", 1) == "1900-03-01");
        assert (DateCalculation.subtract_days ("2000-03-01", 1) == "2000-02-29");
        assert (DateCalculation.subtract_days ("1900-03-01", 1) == "1900-02-28");
        assert (DateCalculation.add_days ("1999-12-31", 1) == "2000-01-01");
        assert (DateCalculation.subtract_days ("2000-01-01", 1) == "1999-12-31");
        assert (DateCalculation.add_days ("2000-03-01", -1) == "2000-02-29");
        assert (DateCalculation.subtract_days ("2000-02-29", -1) == "2000-03-01");
        assert (DateCalculation.add_days ("0001-01-01", 3652058) == "9999-12-31");
        assert (DateCalculation.subtract_days ("9999-12-31", 3652058) == "0001-01-01");
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

private void test_bounds ()
{
    expect_outside ("0001-01-01", 1, true);
    expect_outside ("0001-01-01", -1, false);
    expect_outside ("9999-12-31", 1, false);
    expect_outside ("9999-12-31", -1, true);
    expect_outside ("2000-01-01", int64.MAX, false);
    expect_outside ("2000-01-01", int64.MIN, false);
    expect_outside ("2000-01-01", int64.MAX, true);
    expect_outside ("2000-01-01", int64.MIN, true);
}

private void test_offset_input ()
{
    string[] invalid = { "", "+", "-", "1.5", "1e2", "0x10", "1,000", "1 day", "--1",
                         "9223372036854775808", "-9223372036854775809" };
    foreach (var text in invalid)
        expect_bad_offset (text);
    try
    {
        assert (DateCalculation.parse_offset ("  +08  ") == 8);
        assert (DateCalculation.parse_offset ("-08") == -8);
        assert (DateCalculation.parse_offset ("0") == 0);
        assert (DateCalculation.parse_offset ("9223372036854775807") == int64.MAX);
        assert (DateCalculation.parse_offset ("-9223372036854775808") == int64.MIN);
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

private void test_round_trips ()
{
    try
    {
        // Different months and all century rules across a complete Gregorian cycle.
        for (int year = 1600; year < 2000; year++)
        {
            for (int month = 1; month <= 12; month++)
            {
                string start = "%04d-%02d-01".printf (year, month);
                int[] offsets = { -367, -1, 0, 1, 367 };
                foreach (int offset in offsets)
                {
                    string end = DateCalculation.add_days (start, offset);
                    assert (DateCalculation.days_between (start, end) == offset);
                    assert (DateCalculation.subtract_days (end, offset) == start);
                }
            }
        }
    }
    catch (DateCalculationError failure) { assert_not_reached (); }
}

public static int main (string[] args)
{
    Test.init (ref args);
    Test.add_func ("/date/validation", test_date_validation);
    Test.add_func ("/date/differences", test_differences);
    Test.add_func ("/date/leap-ranges", test_leap_ranges);
    Test.add_func ("/date/offsets", test_offsets);
    Test.add_func ("/date/bounds", test_bounds);
    Test.add_func ("/date/offset-input", test_offset_input);
    Test.add_func ("/date/round-trips", test_round_trips);
    return Test.run ();
}
