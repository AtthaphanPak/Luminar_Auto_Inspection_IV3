import sys
import os
import glob
from datetime import datetime
import configparser
from PyQt6 import uic
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox

from CloseEvent import ConfirmCloseMixin
from Login_window import LoginWindow
from Instructions_window import InstructionWindow
from Vision_Command import send_command
from webservice import FITS_Web_Serivce
import fitsdll

class MainAppWindow(QMainWindow, ConfirmCloseMixin):
    def __init__(self):
        super().__init__()
        config = configparser.ConfigParser()
        try:
            config.read("C:\Projects\AOI_SCANNER\Properties\Config.ini")
            self.CAM1_IP = config["CAMERA"]["CAMERA_1_IP"]
            self.CAM1_PORT = int(config["CAMERA"]["CAMERA_1_PORT"])
            self.CAM1_prom_num = int(config["CAMERA"]["CAMERA_1_PROGRAM_NUM"])
            self.model = config["DEFAULT"]["MODEL"]
            self.operation = config["DEFAULT"]["OPERATION"]
            self.pathimage = config["DEFAULT"]["ImagePath"]
        except Exception as e:
            print(f"{e}\nPlease check config.ini")
            quit()
            
        # self.fitsserivce = FITS_Web_Serivce()
        # if self.fitsserivce.getStatusURL != "OK":
        #     QMessageBox.critical(self, "FITs Message", "Fail To connect Database FITs")
        #     quit()
        
        self.sn = ""
        self.mode = ""
        self.promname = ""
        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Main_GUI.ui", self)

        self.stackedWidget.setCurrentIndex(0)

        # Load KEYENCE Web Monitor 
        self.LoadWeb.load(QUrl(f"http://{self.CAM1_IP}/iv3-wm.html"))
        self.LoadWeb.page().runJavaScript("document.body.style.zoom='67%'")
        self.LoadWeb.loadFinished.connect(self.on_web_loaded)
        
        self.PassButton.clicked.connect(self.open_result)
        self.RetryButton.clicked.connect(self.start_trigger_flow)

        QTimer.singleShot(100, self.start_login_flow)
          
    def start_login_flow(self):
        print("LOGIN")
        self.setEnabled(False)

        self.login = LoginWindow()        
        if self.login.exec() != QDialog.DialogCode.Accepted:
            print("CLOSE")
            QApplication.quit()
            quit() 
        self.enDisplay.setText(self.login.user_input)
            
        QTimer.singleShot(100, self.start_instruction_flow)
        
    def start_instruction_flow(self):
        print("INSTRUCTION")
        self.Instruction = InstructionWindow(index=0)
        if self.Instruction.exec() != QDialog.DialogCode.Accepted:
            print("User Cancel")
            return
        self.mode = self.Instruction.selected_mode
        
        if self.mode == "LOGOUT":
            self.Mainlabel.setText("Waiting . . .")
            self.stackedWidget.setCurrentIndex(0)
            QTimer.singleShot(100, self.start_login_flow)
        
        else:
            self.sn = self.Instruction.serial_value
            self.operation = self.operation

            if self.mode.upper() == "PRODUCTION":
                shake = fitsdll.fn_Handshake(self.model, self.operation, self.sn)
                if shake != True:
                    print("HandCheck Fail")
                    QMessageBox.critical(self, "FITs Message", f"Handcheck FAIL Serial: {self.sn}")
                    QTimer.singleShot(100, self.start_instruction_flow)
                    return
            
            self.serialDisplay.setText(self.sn)
            self.ModeDisplay.setText(self.mode)
            self.StationDisplay.setText(self.operation)
        
            QTimer.singleShot(100, self.operation_sclect)
    
    def operation_sclect(self):
        print("OPERATION")
        self.PassButton.hide()
        self.NextButton.hide()
        self.RetryButton.hide()
        
        self.start_trigger_flow("26")
       
    def start_trigger_flow(self, program_num):
        print("TRIGGER")
        # change program number
        send_command(self.CAM1_IP, self.CAM1_PORT, f'PW,{program_num}\r')
        print("change program number")
        # Write filename
        response = send_command(self.CAM1_IP, self.CAM1_PORT, f'FNW,1,0,{self.sn}\r')
        print("Write filename")
        if response.split(":")[0] != "TCP Error":
            # trigger Result
            response = send_command(self.CAM1_IP, self.CAM1_PORT, 'T2\r')
            print("trigger Result")
            if response.split(":")[0] != "TCP Error":
                self.setEnabled(True)
                self.stackedWidget.setCurrentIndex(1)
                self.Load_screen(response)
            else:
                print(response)
        else:
            self.setEnabled(True)
            self.Mainlabel.setText("FAIL\ncan't communicate with camera, please contact your supervisor")
        
    def Load_screen(self, response):
        if response.split(",")[2].upper() == "OK":
            self.PassButton.show()
            self.NextButton.show()
        
        elif response.split(",")[2].upper() == "NG":
            self.PassButton.show() 
            self.RetryButton.show()

    def on_web_loaded(self, ok: bool):
        print("LOAD WEB")
        if not ok:
            self.setEnabled(True)
            self.Mainlabel.setText("FAIL\nLOADING KEYENCE MONITOR, please contact your supervisor")
            
    def open_result(self):
        self.setEnabled(False)
        print("upload_result")
        log = fitsdll.fn_Log(self.model, self.operation, self.pa)

        PassInstruction = InstructionWindow(index=2)
        result = PassInstruction.exec()
        
        if result == QDialog.DialogCode.Accepted:
            self.start_instruction_flow()
        else:
            self.start_instruction_flow()

        self.setEnabled(True)

    def upload_to_fits_flow(self,):
        pattern = os.path.join(self.pathimage, self.promname, datetime.now().strftime("%b%d%Y"), "*", "*", self.sn + "_*.jpeg")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainAppWindow()
    main_window.showMaximized()
    sys.exit(app.exec())