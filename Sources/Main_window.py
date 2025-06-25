import os
import sys
import glob
import json
import configparser
from PyQt6 import uic
from datetime import datetime
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox

from Login_window import LoginWindow
from Instructions_window import InstructionWindow
from SubPart_window import SubPartWindow
from Vision_Command import send_command
from fitsdll import Convert_Data, fn_Handshake, fn_Log, fn_Query
from Logic.operation_handler import generate_csv, upload_result_to_fits 

class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
        self.exit_confirm_enabled = True
        self.config = configparser.ConfigParser()
        try:
            self.config.read("C:\Projects\AOI_SCANNER\Properties\Config.ini")
            self.CAM1_IP = self.config["CAMERA"].get("CAMERA_1_IP", "")
            self.CAM1_PORT = int(self.config["CAMERA"].get("CAMERA_1_PORT", ""))
            self.CAM2_IP = self.config["CAMERA"].get("CAMERA_2_IP", "")
            self.CAM2_PORT = int(self.config["CAMERA"].get("CAMERA_2_PORT", ""))
            self.model = self.config["DEFAULT"].get("MODEL", "")
            self.operationlist = self.config["DEFAULT"].get("OPERATION", "").split(",")
            self.pathimage = self.config["DEFAULT"].get("ImagePath", "")
            self.LogPath = self.config["DEFAULT"].get("LogPath", "")
        except Exception as e:
            QMessageBox.critical(None, "Close Program", f"{e}\nPlease check config.ini")
            self.exit_confirm_enabled = False
            quit()

        os.makedirs(self.LogPath, exist_ok=True)

        folder_bin = os.path.join(self.pathimage, "bin")
        os.makedirs(folder_bin, exist_ok=True)
        excess_files = glob.glob(os.path.join(self.pathimage, "*.jpeg"))
        if excess_files:
            for flie in excess_files:
                os.rename(flie, os.path.join(folder_bin, os.path.basename(flie)))

        self.mode = ""
        self.en = ""
        self.operation = ""
        self.sn = ""
        self.type = ""
        self.promname = ""
        self.serial_log_path = ""
        self.retries_path = ""
        self.df_subpart = {}
        self.program_list = []
        self.program_index = 0
        self.All_Result = []

        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Main_GUI.ui", self)

        self.stackedWidget.setCurrentIndex(0)
        self.LoadWeb.setZoomFactor(0.50)

        # action Button 
        self.PassButton.clicked.connect(self.open_result)
        self.RetryButton.clicked.connect(self.retries)
        self.NextButton.clicked.connect(self.handle_next_button)
        self.LogoutButton.clicked.connect(self.logout)

        QTimer.singleShot(100, self.start_login_flow)
          
    def start_login_flow(self):
        # print("LOGIN")
        self.setEnabled(False)

        self.login = LoginWindow()        
        if self.login.exec() != QDialog.DialogCode.Accepted:
            # print("CLOSE")
            self.exit_confirm_enabled = False
            QApplication.quit()
            quit() 

        self.en = self.login.user_input
        self.enDisplay.setText(self.en)
            
        QTimer.singleShot(100, self.start_instruction_flow)

    def logout(self):
        self.Mainlabel.setText("Waiting . . .")
        self.stackedWidget.setCurrentIndex(0)
        QTimer.singleShot(100, self.start_login_flow)

    def start_instruction_flow(self):
        # print("INSTRUCTION")
        self.Instruction = InstructionWindow(index=0)
        if self.Instruction.exec() != QDialog.DialogCode.Accepted:
            # print("User Cancel")
            return
        self.type = "N/A"
        
        if self.type == "LOGOUT":
            return self.logout()
        else:
            self.sn = self.Instruction.serial_value
            self.operation = self.operationlist[0]
            self.mode = self.Instruction.mode

            if self.mode.upper() == "PRODUCTION":
                handshake_status = fn_Handshake(self.model, self.operation, self.sn)
                if handshake_status != True:
                    QMessageBox.critical(self, "FITs Message", f"Handcheck FAIL Serial: {self.sn}")
                    QTimer.singleShot(100, self.start_instruction_flow)
                    return
            
            now = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            self.serial_log_path = os.path.join(self.LogPath, f"{self.sn}_{now}")
            self.retries_path = os.path.join(self.serial_log_path, "Log_Retries")
            os.makedirs(self.serial_log_path, exist_ok=True)
            os.makedirs(self.retries_path, exist_ok=True)

            self.subserial = SubPartWindow()
            
            if self.subserial.exec() != QDialog.DialogCode.Accepted:
                return

            self.df_subpart = self.subserial.sub_serial

            self.serialDisplay.setText(self.sn)
            self.TypeDisplay.setText(self.type)
            self.StationDisplay.setText(self.operation)
            self.ModeDisplay.setText(self.mode)
            self.All_Result = []

            QTimer.singleShot(100, self.operation_select)
    
    def operation_select(self):
        # print("OPERATION")
        self.PassButton.hide()
        self.NextButton.hide()
        self.RetryButton.hide()

        call_program = self.config[self.operation].get("CALL_PROGRAM", "{}")
        self.program_list = json.loads(call_program)
        # print(self.program_list)
        self.trigger_program_list()


    def trigger_program_list(self):
        # print("trigger_program_list")
        self.program_pairs =[]
        for cam, prog_list in self.program_list.items():
            for prog in prog_list:
                self.program_pairs.append((cam, prog))

        self.program_index= 0
        self.All_Result = []
        self.Total_item.setText(str(len(self.program_pairs)))
        self.Inspected_item.setText("0")

        self.NextButton.hide()
        self.PassButton.hide()    
        self.RetryButton.hide()           

        self.trigger_current_program()

    def trigger_current_program(self):
        if self.program_index < len(self.program_pairs):
            print(self.program_pairs[self.program_index])
            camera, program = self.program_pairs[self.program_index]
            print(f"Trigger Camera: {camera} ---> program: {program}")
            self.start_trigger_flow()
        else:
            # print("All program completed.")
            self.NextButton.hide()
            self.PassButton.show()

    def handle_next_button(self):
        ## เพิ่ม image ตรงนี้
        self.NextButton.hide()
        self.program_index += 1
        self.trigger_current_program()

    def retries(self):
        # print("retries")
        pattern = f"{self.sn}_*.jpeg"
        retry_images = glob.glob(os.path.join(self.pathimage ,pattern))
        if retry_images:
            for retry_img in retry_images:
                self.move_image(self.retries_path, retry_img)
            
        self.start_trigger_flow()
    
    def start_trigger_flow(self):
        # print("TRIGGER")
        camera_num, program_num = self.program_pairs[self.program_index]
        print("camera_num\t", camera_num)
        print("program_num\t", program_num)
        if int(camera_num) == 1:
            IP = self.CAM1_IP
            PORT = self.CAM1_PORT
        elif int(camera_num) == 2:
            IP = self.CAM2_IP
            PORT = self.CAM2_PORT    
             
        # Load KEYENCE Web Monitor 
        # print("on_web_loaded")
        url_str = f"http://{IP}/iv3-wm.html"
        if self.LoadWeb.url().toString() != url_str:
            self.LoadWeb.load(QUrl(url_str))
        if not hasattr(self, "web_loaded_connected"):
            self.LoadWeb.loadFinished.connect(self.on_web_loaded)
            self.web_loaded_connected = True

        # change program number
        send_command(IP, PORT, f'PW,{program_num}\r')
        # print("change program number")
        # Write filename
        response = send_command(IP, PORT, f'FNW,1,0,{self.sn}\r')
        # print("Write filename")
        if response.split(":")[0] != "TCP Error":
            # trigger Result
            response = send_command(IP, PORT, 'T2\r')
            # print("trigger Result")
            if response.split(":")[0] != "TCP Error":
                self.setEnabled(True)
                if self.stackedWidget.currentIndex() != 1:
                    self.stackedWidget.setCurrentIndex(1)
                program_number_str = "0" + program_num
                response = response.replace("RT", f"CAM{camera_num},{program_number_str}")
                self.Load_screen(response)
                self.Inspected_item.setText(str(self.program_index + 1))
                if self.program_index == len(self.program_pairs) - 1:
                    self.NextButton.hide()
                    self.PassButton.show()
                else:
                    self.NextButton.show()
                    self.PassButton.hide()

        else:
            self.setEnabled(True)
            QMessageBox.critical(self, "ERROR MESSAGE", "FAIL\ncan't communicate with camera, please contact your supervisor")
            self.exit_confirm_enabled = False
            QApplication.quit()
        
    def Load_screen(self, response):
        print(response)
        if len(self.All_Result) <= self.program_index:
            self.All_Result.append(response)
        else:
            self.All_Result[self.program_index] = response
        
        result = response.split(",")[3].upper()
        print(result)
        if result == "OK":
            self.NextButton.show()
            self.RetryButton.hide()
        
        elif result == "NG":
            self.NextButton.show()
            self.RetryButton.show()
        else:
            QMessageBox.critical(self, "Result ERROR", "Can not find result status from camera response signal.")

    def on_web_loaded(self, ok: bool):
        # print("LOAD WEB")
        if not ok:
            self.setEnabled(True)
            QMessageBox.critical(self, "ERROR MESSAGE", "FAIL\nLOADING KEYENCE MONITOR, Please contact your supervisor")
            self.exit_confirm_enabled = False
            QApplication.quit()
            
    def open_result(self):
        # print("upload_result")
        self.setEnabled(False)

        data_dict = {
            "Operation": self.operation,
            # "Program name": [],
            "Result": [],
            "Image Path": [],
        }

        for row in self.All_Result:
            # print(row)
            now = datetime.now().strftime("%b%d%Y")
            # image_num = "{:05d}".format(int(row.split(",")[2]) + 1)
            program = row.split(",")[1]
            final_result = row.split(",")[3].replace("OK", "PASS").replace("NOK", "FAIL").replace("--", "FAIL")
            pattern = f"{self.sn}_*_{program}_*_{now}_*.jpeg"
            img_path = self.find_result_img(pattern)

            # data_dict["Program name"].append("Sta")
            data_dict["Result"].append(final_result)
            data_dict["Image Path"].append(img_path)

        
        if "Result" in data_dict and all(val == "PASS" for val in data_dict["Result"]):
            data_dict["Final Result"] = "PASS"
        else: 
            data_dict["Final Result"] = "FAIL"

        wo = fn_Query(self.model, self.operation, self.sn, "WO#")

        fits_df = {
            "EN": self.en,
            "SN Scanner": self.sn,
            "WO#": wo
        }
        fits_df.update(self.df_subpart)

        fits_df.update(upload_result_to_fits(data_dict))
        
        # print("DATAFRAME\n",fits_df)
        generate_csv(self.serial_log_path, fits_df)

        if self.mode.upper() == "PRODUCTION":
            parameters = Convert_Data(fits_df.keys())
            values = Convert_Data(fits_df.values())
            log_status = fn_Log(self.model, self.operation, parameters, values)
            if log_status == True:
                QMessageBox.information(self, "FITs success", "Success uploaded data to FITs")
            else:
                QMessageBox.critical(self, "Failed uploaded data to FITs", log_status)
                

        PassInstruction = InstructionWindow(index=1)
        result = PassInstruction.exec()
        
        if result == QDialog.DialogCode.Accepted:
            self.start_instruction_flow()
        else:
            self.start_instruction_flow()

        self.setEnabled(True)

    def find_result_img(self, pattern: str):
        files = glob.glob(os.path.join(self.pathimage ,pattern))
        if not files:
            return None
        latest_file = max(files, key=os.path.getmtime)
        return self.move_image(self.serial_log_path, latest_file)

    def move_image(self, path, target_pathfile):
        des_path = os.path.join(path, os.path.basename(target_pathfile))
        try:
            os.rename(target_pathfile, des_path)
            return des_path
        except Exception as e:
            QMessageBox.warning(self, "Move file Error", e)
            return ""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainAppWindow()
    main_window.showFullScreen()
    sys.exit(app.exec())