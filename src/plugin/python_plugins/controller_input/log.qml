import QtQuick

Item {
    // The Windows API log actor writes to a different sink from the GUI logger.
    Timer {
        interval: 100
        running: true
        repeat: true
        onTriggered: {
            var records = python_callback("take_log_records")
            if (!Array.isArray(records)) {
                stop()
                helpers.logError("Controller Log bridge failed: " + records)
                return
            }
            for (var i = 0; i < records.length; ++i) {
                var record = records[i]
                logger.sourceModel.appendLog(new Date(record[0]), record[1], record[2])
            }
        }
    }
}
