frappe.ui.form.on("Sales Order", {
    refresh: function(frm) {
        frm.add_custom_button("Sales Order", function() {
            console.log("Sales Order");
        });
    }
});