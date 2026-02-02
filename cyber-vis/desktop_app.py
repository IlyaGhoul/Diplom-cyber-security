"""
Супер-минимальное приложение для авторизации
"""
import sys
import requests
from PyQt6 import QtWidgets, QtCore
from src.cyber_vis.app.scripts.loginui import Ui_MainWindow

class LoginWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Базовая настройка
        self.setFixedSize(self.size())
        self.setWindowTitle("Вход")
        self.ui.lineEdit_2.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ui.lineEdit.setText("ilya")
        self.ui.lineEdit_2.setText("1111")
        self.ui.pushButton.setText("Войти")
        self.ui.pushButton_2.setText("Закрыть")
        
        # Подключение
        self.ui.pushButton.clicked.connect(self.login)
        self.ui.pushButton_2.clicked.connect(self.close)
    
    def login(self):
        username = self.ui.lineEdit.text().strip()
        password = self.ui.lineEdit_2.text().strip()
        
        if not username or not password:
            return
        
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton.setText("...")
        
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": username, "password": password, "client_type": "desktop"},
                timeout=3
            )
            
            if response.json().get("success"):
                self.ui.pushButton.setText("✓")
                self.ui.pushButton.setStyleSheet("background-color: green; color: white;")
                QtWidgets.QApplication.processEvents()
                QtCore.QTimer.singleShot(500, self.close)
            else:
                self.ui.pushButton.setText("✗")
                self.ui.pushButton.setStyleSheet("background-color: red; color: white;")
                QtCore.QTimer.singleShot(1000, self.reset_button)
                
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            self.ui.pushButton.setText("✗")
            self.ui.pushButton.setStyleSheet("background-color: orange; color: white;")
            QtCore.QTimer.singleShot(1000, self.reset_button)
    
    def reset_button(self):
        self.ui.pushButton.setEnabled(True)
        self.ui.pushButton.setText("Войти")
        self.ui.pushButton.setStyleSheet("")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())