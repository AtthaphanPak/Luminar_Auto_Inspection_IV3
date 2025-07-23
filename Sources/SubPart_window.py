from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from CloseEvent import ConfirmCloseMixin

class SubPartWindow(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Sub-Part_window.ui", self)
        print(type(self.XCVR))
        self.XCVR.setFocus()
        self.XCVR.returnPressed.connect(self.PCBA.setFocus)
        print("PCBA")
        self.PCBA.returnPressed.connect(self.Poly_Sensor.setFocus)
        self.Poly_Sensor.returnPressed.connect(self.Poly_MES.setFocus)
        self.Poly_MES.returnPressed.connect(self.Fold.setFocus)
        self.Fold.returnPressed.connect(self.LATM.setFocus)
        self.LATM.returnPressed.connect(self.StartButton.click)
        
        self.StartButton.clicked.connect(self.Start_clicked)
        self.LogoutButton.clicked.connect(self.logout)
        print("SubPartWindow")
        
    def Start_clicked(self):
        self.sub_serial = {
            "SN XCVR": self.XCVR.text(),
            "SN PCBA": self.PCBA.text(),
            "SN Polygon sensor": self.Poly_Sensor.text(),
            "SN Polygon (MES Barcode)": self.Poly_MES.text(),
            "SN Fold Mirror": self.Fold.text(),
            "SN LATM": self.LATM.text()
        }
        print(self.sub_serial)
        self.accept()
    
    def logout(self):
        self.sub_serial = "LOGOUT"
        self.accept()
        
    def closeEvent(self, event):
        return event.ignore()