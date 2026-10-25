/* SPDX-License-Identifier: GPL-3.0-or-later */

public class MathDateDialog : Gtk.Dialog
{
    private Gtk.ComboBoxText operation;
    private Gtk.Entry start_date;
    private Gtk.Entry end_date;
    private Gtk.Entry day_count;
    private Gtk.Label end_label;
    private Gtk.Label days_label;
    private Gtk.Label result;
    private Gtk.Label error;

    public MathDateDialog (Gtk.Window parent)
    {
        Object (title: _("Date Calculation"), transient_for: parent,
                destroy_with_parent: true, resizable: false);
        add_button (_("_Close"), Gtk.ResponseType.CLOSE);
        add_button (_("_Calculate"), Gtk.ResponseType.APPLY);
        set_default_response (Gtk.ResponseType.APPLY);

        var grid = new Gtk.Grid ();
        grid.margin = 18;
        grid.row_spacing = 12;
        grid.column_spacing = 12;
        get_content_area ().pack_start (grid, true, true, 0);

        operation = new Gtk.ComboBoxText ();
        operation.append ("difference", _("Between two dates"));
        operation.append ("add", _("Add days"));
        operation.append ("subtract", _("Subtract days"));
        operation.set_active_id ("difference");
        operation.get_accessible ().set_name (_("Operation"));
        var operation_label = make_label (_("_Operation"), operation);
        grid.attach (operation_label, 0, 0, 1, 1);
        grid.attach (operation, 1, 0, 1, 1);

        var today = new DateTime.now_local ();
        start_date = make_entry (_("Start date"), "YYYY-MM-DD", today.format ("%F"));
        end_date = make_entry (_("End date"), "YYYY-MM-DD", today.format ("%F"));
        day_count = make_entry (_("Number of days"), _("Whole days"), "0");
        day_count.input_purpose = Gtk.InputPurpose.NUMBER;
        grid.attach (make_label (_("_Start date"), start_date), 0, 1, 1, 1);
        grid.attach (start_date, 1, 1, 1, 1);
        end_label = make_label (_("_End date"), end_date);
        grid.attach (end_label, 0, 2, 1, 1);
        grid.attach (end_date, 1, 2, 1, 1);
        days_label = make_label (_("_Number of days"), day_count);
        grid.attach (days_label, 0, 3, 1, 1);
        grid.attach (day_count, 1, 3, 1, 1);

        var hint = new Gtk.Label (_("Use YYYY-MM-DD, from 0001-01-01 to 9999-12-31. Leap-day counts include the earlier date and exclude the later date."));
        hint.wrap = true;
        hint.max_width_chars = 52;
        hint.xalign = 0;
        hint.get_style_context ().add_class ("dim-label");
        grid.attach (hint, 0, 4, 2, 1);

        result = new Gtk.Label ("");
        result.selectable = true;
        result.wrap = true;
        result.max_width_chars = 52;
        result.xalign = 0;
        result.get_accessible ().set_description (_("Date calculation result"));
        result.get_accessible ().set_role (Atk.Role.STATUSBAR);
        grid.attach (result, 0, 5, 2, 1);
        error = new Gtk.Label ("");
        error.wrap = true;
        error.max_width_chars = 52;
        error.xalign = 0;
        error.no_show_all = true;
        error.get_style_context ().add_class ("error");
        error.get_accessible ().set_description (_("Date calculation error"));
        error.get_accessible ().set_role (Atk.Role.ALERT);
        grid.attach (error, 0, 6, 2, 1);

        operation.changed.connect (update_operation);
        start_date.changed.connect (clear_result);
        end_date.changed.connect (clear_result);
        day_count.changed.connect (clear_result);
        response.connect ((response_id) => {
            if (response_id == Gtk.ResponseType.APPLY)
                calculate ();
            else
                destroy ();
        });
        update_operation ();
        start_date.grab_focus ();
        start_date.select_region (0, -1);
    }

    private Gtk.Label make_label (string text, Gtk.Widget target)
    {
        var label = new Gtk.Label.with_mnemonic (text);
        label.mnemonic_widget = target;
        label.xalign = 0;
        return label;
    }

    private Gtk.Entry make_entry (string name, string placeholder, string text)
    {
        var entry = new Gtk.Entry ();
        entry.text = text;
        entry.placeholder_text = placeholder;
        entry.activates_default = true;
        entry.hexpand = true;
        entry.get_accessible ().set_name (name);
        return entry;
    }

    private void clear_result ()
    {
        result.label = "";
        error.label = "";
        error.hide ();
    }

    private void update_operation ()
    {
        bool difference = operation.get_active_id () == "difference";
        end_date.sensitive = difference;
        end_label.sensitive = difference;
        day_count.sensitive = !difference;
        days_label.sensitive = !difference;
        clear_result ();
    }

    private void calculate ()
    {
        clear_result ();
        try
        {
            if (operation.get_active_id () == "difference")
            {
                int days = DateCalculation.days_between (start_date.text, end_date.text);
                int leap_days = DateCalculation.leap_days_between (start_date.text, end_date.text);
                result.label = _("Elapsed days (end minus start): %d\nLeap days: %d").printf (days, leap_days);
            }
            else
            {
                int64 days = DateCalculation.parse_offset (day_count.text);
                string date = operation.get_active_id () == "add"
                    ? DateCalculation.add_days (start_date.text, days)
                    : DateCalculation.subtract_days (start_date.text, days);
                result.label = _("Resulting date: %s").printf (date);
            }
        }
        catch (DateCalculationError failure)
        {
            error.label = failure.message;
            error.show ();
        }
    }
}
