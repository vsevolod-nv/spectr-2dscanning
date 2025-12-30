from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
)
 
class DeviceConnectionCard(QGroupBox):
    def __init__(self, title, device_obj, check_connection_func=None):
        super().__init__(title)
        self.device = device_obj
        self.check_connection_func = check_connection_func 
        self.init_ui()
 
    def init_ui(self):
        layout = QVBoxLayout()

        sel_layout = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItem("Select Device/Port...")
        
        self.refresh_btn = QPushButton("↻") 
        self.refresh_btn.setFixedWidth(30)
        self.refresh_btn.clicked.connect(self.refresh_list)
        
        sel_layout.addWidget(self.combo)
        sel_layout.addWidget(self.refresh_btn)
        
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red")
        
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        btn_layout.addWidget(self.connect_btn)
 
        layout.addLayout(sel_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
 
    def refresh_list(self):
        self.combo.clear()
        self.combo.addItem("Select Device/Port...")
        
        if self.check_connection_func:
            try:
                items = self.check_connection_func() 
                self.combo.addItems(items)
            except Exception as e:
                self.combo.addItem(f"Error: {e}")
 
    def toggle_connection(self):
        if getattr(self.device, "is_connected", False):
            if hasattr(self.device, "disconnect"):
                self.device.disconnect()
            
   
            self.device.is_connected = False 
            self.update_status(False)
        else:
            target = self.combo.currentText()
            if "Select" in target:
                return
 
            try:
                if hasattr(self.device, "connect_by_name"):
                    success = self.device.connect_by_name(target)
                else:
                    self.device.connect() 
                    success = self.device.is_connected
 
                self.update_status(success)
            except Exception as e:
                self.status_label.setText(f"Error: {str(e)}")
                self.status_label.setStyleSheet("color: red")
 
    def update_status(self, is_connected):
        if is_connected:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green")
            self.connect_btn.setText("Disconnect")
        else:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red")
            self.connect_btn.setText("Connect")