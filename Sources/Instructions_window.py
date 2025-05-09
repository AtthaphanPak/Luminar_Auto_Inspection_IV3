from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from CloseEvent import ConfirmCloseMixin

class InstructionWindow(QDialog, ConfirmCloseMixin):
     
    def __init__(self, index=0):
        super().__init__()
        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Instructions_GUI.ui", self)
        self.stackedWidget.setCurrentIndex(index)

        self.LogoutButton.clicked.connect(self.logout)
        self.ApplyButton.clicked.connect(self.Insert_clicked)
        self.ActFailButton.clicked.connect(self.retest_instruction_process)
        self.ActPassButton.clicked.connect(self.retest_instruction_process)
        

    def Insert_clicked(self):
        self.serial_value = self.SerialValue.text()
        if len(self.serial_value ) == 22:
            self.selected_mode = self.ModeValue.currentText()
            self.accept()
        
        else:
            self.label_Error.setText("Please check your Serial Number.")
            self.label_Error.setStyleSheet("color: red;")
        
    def retest_instruction_process(self):
        self.reject()

    def logout(self):
        self.selected_mode = "LOGOUT"
        self.accept()