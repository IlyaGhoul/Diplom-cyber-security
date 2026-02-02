from PyQt6 import QtCore, QtGui, QtWidgets
from loginui import Ui_MainWindow
import sys
import asyncio
import threading
import json
from websocket_client import SimpleWebSocketClient


class LoginWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Фиксируем размер окна
        self.setFixedSize(self.size())
        
        # Устанавливаем заголовок окна
        self.setWindowTitle("Cyber-Vis - Авторизация")
        
        # Настраиваем поле пароля
        self.ui.lineEdit_2.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        
        # Устанавливаем тестовые значения для удобства
        self.ui.lineEdit.setText("ilya")
        self.ui.lineEdit_2.setText("1111")
        
        # Инициализируем WebSocket клиент
        self.ws_client = SimpleWebSocketClient("ws://localhost:8765")
        self.ws_thread = None
        self.is_authenticated = False
        
        # Подключаем кнопки
        self.ui.pushButton_2.clicked.connect(self.close_window)  # Кнопка "Выйти"
        self.ui.pushButton.clicked.connect(self.login)           # Кнопка "Ввойти" (исправьте опечатку в UI)
        
        # Добавляем обработку нажатия Enter
        self.ui.lineEdit.returnPressed.connect(self.login)
        self.ui.lineEdit_2.returnPressed.connect(self.login)
        
    def close_window(self):
        """Закрытие окна"""
        self.close()
    
    def login(self):
        """Обработка попытки входа"""
        username = self.ui.lineEdit.text().strip()
        password = self.ui.lineEdit_2.text().strip()
        
        # Базовая проверка
        if not username or not password:
            QtWidgets.QMessageBox.warning(
                self, 
                "Ошибка", 
                "Заполните все поля!"
            )
            return
        
        # Показываем индикатор загрузки
        self.ui.pushButton.setText("Подключение...")
        self.ui.pushButton.setEnabled(False)
        
        # Запускаем авторизацию в отдельном потоке
        def run_auth():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Пытаемся подключиться к WebSocket серверу
                connected = loop.run_until_complete(self.ws_client.connect())
                
                if connected:
                    # Отправляем данные для авторизации
                    auth_data = {
                        "username": username,
                        "password": password
                    }
                    
                    response = loop.run_until_complete(
                        self.ws_client.send_message(json.dumps(auth_data))
                    )
                    
                    # Парсим ответ
                    if response:
                        try:
                            data = json.loads(response)
                            
                            if data.get("type") == "welcome":
                                # Успешная авторизация
                                self.is_authenticated = True
                                
                                # Обновляем UI из основного потока
                                QtCore.QMetaObject.invokeMethod(self, "_show_success", 
                                    QtCore.Qt.ConnectionType.QueuedConnection,
                                    QtCore.Q_ARG(str, data.get("message", "")))
                                
                                # Запускаем прослушивание сообщений
                                loop.run_until_complete(
                                    self.ws_client.listen_for_messages()
                                )
                            else:
                                # Ошибка авторизации
                                error_msg = data.get("message", "Неизвестная ошибка")
                                QtCore.QMetaObject.invokeMethod(self, "_show_error", 
                                    QtCore.Qt.ConnectionType.QueuedConnection,
                                    QtCore.Q_ARG(str, error_msg))
                                
                        except json.JSONDecodeError:
                            QtCore.QMetaObject.invokeMethod(self, "_show_error", 
                                QtCore.Qt.ConnectionType.QueuedConnection,
                                QtCore.Q_ARG(str, "Ошибка формата ответа сервера"))
                    else:
                        QtCore.QMetaObject.invokeMethod(self, "_show_error", 
                            QtCore.Qt.ConnectionType.QueuedConnection,
                            QtCore.Q_ARG(str, "Нет ответа от сервера"))
                        
                else:
                    QtCore.QMetaObject.invokeMethod(self, "_show_error", 
                        QtCore.Qt.ConnectionType.QueuedConnection,
                        QtCore.Q_ARG(str, "Не удалось подключиться к серверу"))
                    
            except Exception as e:
                QtCore.QMetaObject.invokeMethod(self, "_show_error", 
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, f"Ошибка: {str(e)}"))
                    
            finally:
                loop.close()
                # Возвращаем кнопку в исходное состояние
                QtCore.QMetaObject.invokeMethod(self, "_reset_button", 
                    QtCore.Qt.ConnectionType.QueuedConnection)
        
        # Запускаем авторизацию в фоновом потоке
        thread = threading.Thread(target=run_auth)
        thread.daemon = True
        thread.start()
    
    @QtCore.pyqtSlot(str)
    def _show_success(self, message):
        """Показать сообщение об успешной авторизации (вызывается из основного потока)"""
        QtWidgets.QMessageBox.information(
            self, 
            "Успешный вход", 
            f"{message}\n\nВы успешно авторизовались в системе!"
        )
        
        # Здесь можно открыть главное окно приложения
        # self.open_main_window()
        
        # Пока просто показываем информацию
        self.show_connection_info()
    
    @QtCore.pyqtSlot(str)
    def _show_error(self, message):
        """Показать сообщение об ошибке (вызывается из основного потока)"""
        QtWidgets.QMessageBox.critical(
            self, 
            "Ошибка авторизации", 
            f"Не удалось войти в систему:\n{message}\n\nПроверьте:\n1. Запущен ли WebSocket сервер\n2. Правильность логина и пароля\n3. Подключение к интернету"
        )
    
    @QtCore.pyqtSlot()
    def _reset_button(self):
        """Восстановить состояние кнопки (вызывается из основного потока)"""
        self.ui.pushButton.setText("Ввойти")
        self.ui.pushButton.setEnabled(True)
    
    def show_connection_info(self):
        """Показать информацию о подключении"""
        info_dialog = QtWidgets.QDialog(self)
        info_dialog.setWindowTitle("Информация о подключении")
        info_dialog.setFixedSize(400, 300)
        
        layout = QtWidgets.QVBoxLayout()
        
        label = QtWidgets.QLabel("✅ Вы успешно подключились к системе!")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = label.font()
        font.setPointSize(12)
        label.setFont(font)
        
        info_text = QtWidgets.QTextEdit()
        info_text.setReadOnly(True)
        info_text.append("Статус: Подключено")
        info_text.append(f"Сервер: ws://localhost:8765")
        info_text.append("Пользователь: ilya")
        info_text.append("\nДоступные команды:")
        info_text.append("• Отправка сообщений через WebSocket")
        info_text.append("• Мониторинг соединений")
        info_text.append("• Просмотр статистики")
        
        close_btn = QtWidgets.QPushButton("Закрыть")
        close_btn.clicked.connect(info_dialog.close)
        
        test_btn = QtWidgets.QPushButton("Тест WebSocket")
        test_btn.clicked.connect(self.test_websocket)
        
        layout.addWidget(label)
        layout.addWidget(info_text)
        layout.addWidget(test_btn)
        layout.addWidget(close_btn)
        
        info_dialog.setLayout(layout)
        info_dialog.exec()
    
    def test_websocket(self):
        """Тестирование WebSocket подключения"""
        def run_test():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Отправляем тестовое сообщение
            if self.is_authenticated and self.ws_client.connected:
                test_msg = json.dumps({
                    "type": "test",
                    "message": "Тестовое сообщение от PyQt6 клиента",
                    "timestamp": QtCore.QDateTime.currentDateTime().toString()
                })
                
                try:
                    response = loop.run_until_complete(
                        self.ws_client.send_message(test_msg)
                    )
                    print(f"📨 Ответ сервера: {response}")
                    
                    # Показываем уведомление в UI
                    QtCore.QMetaObject.invokeMethod(self, "_show_test_result", 
                        QtCore.Qt.ConnectionType.QueuedConnection,
                        QtCore.Q_ARG(str, response))
                        
                except Exception as e:
                    print(f"❌ Ошибка теста: {e}")
            
            loop.close()
        
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()
        
        QtWidgets.QMessageBox.information(
            self, 
            "Тест WebSocket", 
            "Тестовое сообщение отправлено. Смотрите консоль для результатов."
        )
    
    @QtCore.pyqtSlot(str)
    def _show_test_result(self, result):
        """Показать результат теста"""
        QtWidgets.QMessageBox.information(
            self,
            "Результат теста",
            f"Получен ответ от сервера:\n{result[:200]}..." if len(result) > 200 else f"Получен ответ от сервера:\n{result}"
        )


def main():
    """Главная функция для запуска приложения"""
    app = QtWidgets.QApplication(sys.argv)
    
    # Настраиваем стиль приложения
    app.setStyle("Fusion")
    
    # Создаем палитру для темной темы
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 0, 0))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(142, 45, 197))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()