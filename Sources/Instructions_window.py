from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QInputDialog, QComboBox, QMessageBox, QLineEdit
from Logic.operation_handler import is_valid_serial

class InstructionWindow(QDialog):
     
    def __init__(self, index=0):
        super().__init__()

        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Instructions_GUI.ui", self)
        self.mode = "Production"
        
        self.stackedWidget.setCurrentIndex(index)

        self.SerialValue.setFocus()

        self.LogoutButton.clicked.connect(self.logout)
        self.ApplyButton.clicked.connect(self.Insert_clicked)
        self.ActionButton.clicked.connect(self.retest_instruction_process)
        self.ModeButton.clicked.connect(self.select_mode)
        
    def Insert_clicked(self):
        self.serial_value = self.SerialValue.text()
        if is_valid_serial(self.serial_value):
            self.accept()
        
        else:
            self.label_Error.setText("Please check your Serial Number.")
            self.label_Error.setStyleSheet("color: red;")
        
    def retest_instruction_process(self):
        self.reject()

    def select_mode(self):
        password, ok = QInputDialog.getText(self, "Admin login", "Enter admin password:", QLineEdit.EchoMode.Password)
        if ok and password == "Admin123":
            mode_dialog = QInputDialog()
            mode, ok2 = QInputDialog.getItem(self, "Select Mode", "Choose mode:",["Production", "Debug"], 0, False)
            if ok2:
                self.mode = mode
        else:
            QMessageBox.warning(self, "Asscess Denied", "Incorrect password.")

    def logout(self):
        self.selected_type = "LOGOUT"
        self.accept()

    def closeEvent(self, event):
        return event.ignore()