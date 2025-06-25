from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from CloseEvent import ConfirmCloseMixin

class SubPartWindow(QDialog, ConfirmCloseMixin):
    def __init__(self):
        super().__init__()
        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Sub-Part_window.ui", self)
        
        self.XCVR.setFocus()
        self.XCVR.returnPressed.connect(self.LoginButton.click)
        self.PCBA.returnPressed.connect(self.Poly_sensor.setFocus)
        self.Poly_sensor.returnPressed.connect(self.Poly_MES.setFocus)
        self.Poly_MES.returnPressed.connect(self.Fold.setFocus)
        self.Fold.returnPressed.connect(self.LATM.setFocus)

        self.LATM.clicked.connect(self.login_clicked)
        
    def login_clicked(self):
        self.sub_serial = {
            "SN XCVR": self.XCVR.text(),
            "SN PCBA": self.PCBA.text(),
            "SN Polygon sensor": self.Poly_sensor.text(),
            "SN Polygon (MES Barcode)": self.Poly_MES.text(),
            "SN Fold Mirror": self.Fold.text(),
            "SN LATM": self.LATM.text()
        }
        self.accept()