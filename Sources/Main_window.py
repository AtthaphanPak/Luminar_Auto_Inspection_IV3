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
from Vision_Command import send_command, check_IV3_connection
from fitsdll import Convert_Data, fn_Handshake, fn_Log, fn_Query
from Logic.operation_handler import generate_csv, upload_result_to_fits 

class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
        self.exit_confirm_enabled = True
        self.config = configparser.ConfigParser()
        pcname = os.environ['COMPUTERNAME']
        print(pcname)
        try:
            self.config.read("C:\Projects\AOI_SCANNER\Properties\Config.ini")
            self.CAM1_IP = self.config["CAMERA"].get("CAMERA_1_IP", "")
            self.CAM1_PORT = int(self.config["CAMERA"].get("CAMERA_1_PORT", ""))
            self.CAM2_IP = self.config["CAMERA"].get("CAMERA_2_IP", "")
            self.CAM2_PORT = int(self.config["CAMERA"].get("CAMERA_2_PORT", ""))
            self.model = self.config[pcname].get("MODEL", "")
            self.operationlist = self.config[pcname].get("OPERATION", "").split(",")
            self.pathimage = self.config["DEFAULT"].get("ImagePath", "")
            self.LogPath = self.config["DEFAULT"].get("LogPath", "")
        except Exception as e:
            QMessageBox.critical(None, "Close Program", f"{e}\nPlease check config.ini")
            self.exit_confirm_enabled = False
            quit()

        os.makedirs(self.LogPath, exist_ok=True)
        
        self.clear_log()
        
        self.en = ""
        self.operation = ""
        self.sn = ""
        self.promname = ""
        self.serial_log_path = ""
        self.retries_path = ""
        self.program_list = []
        self.program_index = 0
        self.All_Result = []
        self.Result_images = []

        uic.loadUi("C:\Projects\AOI_SCANNER\Sources\GUI\Main_GUI.ui", self)

        self.stackedWidget.setCurrentIndex(0)
        self.LoadWeb.setZoomFactor(0.67)

        # action Button 
        self.PassButton.clicked.connect(self.open_result)
        self.RetryButton.clicked.connect(self.retries)
        self.NextButton.clicked.connect(self.handle_next_button)
        self.LogoutButton.clicked.connect(self.logout)

        self.check_required_camera_connction()
        QTimer.singleShot(100, self.start_login_flow)

    def clear_log(self):
        self.result_image_list = []
        self.result_txt_list = []
        folder_bin = os.path.join(self.pathimage, "bin")
        os.makedirs(folder_bin, exist_ok=True)
        jpeg_files = glob.glob(os.path.join(self.pathimage, "*.jpeg"))
        txt_files = glob.glob(os.path.join(self.pathimage, "*.txt"))
        
        excess_files = jpeg_files + txt_files
        if excess_files:
            for flie in excess_files:
                os.rename(flie, os.path.join(folder_bin, os.path.basename(flie)))

    def check_required_camera_connction(self):
        operation_sections = self.operationlist
        required_cameras = set()
        for operation in operation_sections:
            call_program_str = self.config[operation].get("CALL_PROGRAM", "{}")
            try:
                call_program_dict = json.loads (call_program_str)
                for cam in call_program_dict.keys():
                    required_cameras.add(int(cam))
            except Exception as e:
                QMessageBox.critical(self,"ERROR Program", f"Error paring CALL_PROGRAM {operation}: {e}")

            errors = []
            if 1 in required_cameras and not check_IV3_connection(self.CAM1_IP, self.CAM1_PORT):
                errors.append(f"Cannot connect to CAMERA 1 {self.CAM1_IP})")
            if 2 in required_cameras and not check_IV3_connection(self.CAM1_IP, self.CAM2_PORT):
                errors.append(f"Cannot connect to CAMERA 2 {self.CAM2_IP})")            

            if errors:
                QMessageBox.critical(self, "Camera Connection Error", "\n".join(errors))
                self.exit_confirm_enabled = False
                QApplication.quit()
                quit()

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
            
        QTimer.singleShot(100, self.start_instruction_flow)

    def logout(self):
        self.move_retries()
        self.clear_log()
        self.Mainlabel.setText("Waiting . . .")
        self.Operatio_ID.setText("")
        self.stackedWidget.setCurrentIndex(0)
        QTimer.singleShot(100, self.start_login_flow)

    def start_instruction_flow(self):
        print("INSTRUCTION")
        self.Instruction = InstructionWindow(index=0)
        if self.Instruction.exec() != QDialog.DialogCode.Accepted:
            # print("User Cancel")
            return
        self.mode = self.Instruction.mode
        
        if self.mode == "LOGOUT":
            return self.logout()
        else:
            sn = self.Instruction.serial_value
            if self.mode.upper() == "PRODUCTION":
                for operation_choice in self.operationlist:
                    print(self.model)
                    print(operation_choice)
                    print(sn)
                    handshake_status = fn_Handshake(self.model, operation_choice, sn)
                    print(handshake_status)
                    if handshake_status == True:   
                        self.operation = operation_choice
                        self.Operatio_ID.setText(operation_choice)
                        self.sn = sn
                        self.mode = self.Instruction.mode
                        break
                else: 
                    QMessageBox.critical(self, "Handcheck FAIL", f"Serial: {sn} has no test in this station.")
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

            if self.df_subpart == "LOGOUT":
                return self.logout()

            self.enDisplay.setText(self.en)
            self.serialDisplay.setText(self.sn)
            self.StationDisplay.setText(self.operation)
            self.ModeDisplay.setText(self.mode)
            self.All_Result = []

            QTimer.singleShot(100, self.operation_select)
    
    def operation_select(self):
        print("OPERATION")
        self.PassButton.hide()
        self.NextButton.hide()
        self.RetryButton.hide()
        print(self.operation)
        call_program = self.config[self.operation].get("CALL_PROGRAM", "{}")
        self.program_list = json.loads(call_program)
        # print(self.program_list)
        self.trigger_program_list()


    def trigger_program_list(self):
        print("trigger_program_list")
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
            camera, program = self.program_pairs[self.program_index]
            print(f"Trigger Camera: {camera} ---> program: {program}")
            self.start_trigger_flow()
        else:
            # print("All program completed.")
            self.NextButton.hide()
            self.PassButton.show()

    def handle_next_button(self):
        camera, program = self.program_pairs[self.program_index]
        jpeg_path, txt_path  = self.find_result_files(self.serial_log_path, program)
        print("Save path:\t", jpeg_path)
        self.Result_images.append(jpeg_path)
        self.NextButton.hide()
        self.program_index += 1
        self.trigger_current_program()

    def retries(self):
        # print("retries")
        pattern_base = os.path.join(self.pathimage, f"{self.sn}_")
        
        jpeg_files = glob.glob(pattern_base + "*.jpeg")
        txt_files = glob.glob(pattern_base + "*.txt")
            
        if jpeg_files:
            latest_jpeg = max(jpeg_files, key=os.path.getmtime)
            if latest_jpeg:
                self.move_files(self.retries_path, latest_jpeg)
     
        if txt_files:
            latest_txt = max(txt_files, key=os.path.getmtime)
            if latest_txt:
                self.move_files(self.retries_path, latest_txt)
        
        self.start_trigger_flow()
        
    def move_retries(self):
        pattern_base = os.path.join(self.pathimage, f"{self.sn}_")
        
        jpeg_files = glob.glob(pattern_base + "*.jpeg")
        txt_files = glob.glob(pattern_base + "*.txt")
            
        if jpeg_files:
            latest_jpeg = max(jpeg_files, key=os.path.getmtime)
            if latest_jpeg:
                self.move_files(self.retries_path, latest_jpeg)
     
        if txt_files:
            latest_txt = max(txt_files, key=os.path.getmtime)
            if latest_txt:
                self.move_files(self.retries_path, latest_txt)        
    
    def start_trigger_flow(self):
        # print("TRIGGER")
        camera_num, program_num = self.program_pairs[self.program_index]
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
        last_program = self.program_pairs[-1][1]
        jpeg_path, txt_path = self.find_result_files(self.serial_log_path, last_program)
        self.Result_images.append(jpeg_path)
        
        data_dict = {
            "Operation": self.operation,
            "SN": self.sn,
            "Result": [],
            "Score": [],
            "Image Path": [],
        }
        
        for row in self.All_Result:
            now = datetime.now().strftime("%b%d%Y")
            rowdata = row.split(",")
            program = rowdata[1]
            final_result = rowdata[3].replace("OK", "PASS").replace("NG", "FAIL").replace("--", "FAIL")
            score_result = rowdata[9]
           
            data_dict["Result"].append(final_result)
            data_dict["Score"].append(score_result)
            
        for img_path in self.Result_images:
            data_dict["Image Path"].append(img_path)
            print(img_path)

        
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
                
        self.Result_images = []
        PassInstruction = InstructionWindow(index=2)
        result = PassInstruction.exec()
        
        if result == QDialog.DialogCode.Accepted:
            self.start_instruction_flow()
        else:
            self.start_instruction_flow()

        self.setEnabled(True)

    def find_result_files(self, des_path, program_num: str):
        now = datetime.now().strftime("%b%d%Y")
        pattern_base = os.path.join(self.pathimage, f"{self.sn}_*_0{program_num}_*_{now}_")
        print(pattern_base)
        
        jpeg_files = glob.glob(pattern_base + "*.jpeg")
        latest_jpeg = max(jpeg_files, key=os.path.getmtime)
        if latest_jpeg:
            img_path = self.move_files(des_path, latest_jpeg)
        
        txt_files = glob.glob(pattern_base + "*.txt")
        latest_txt = max(txt_files, key=os.path.getmtime)
        if latest_txt:
            txt_path = self.move_files(des_path, latest_txt)
        
        return img_path, txt_path

    def move_files(self, path, target_pathfile):
        des_path = os.path.join(path, os.path.basename(target_pathfile))
        try:
            os.rename(target_pathfile, des_path)
            return des_path
        except Exception as e:
            QMessageBox.warning(self, "Move file Error", e)
            return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainAppWindow()
    main_window.showFullScreen()
    sys.exit(app.exec())