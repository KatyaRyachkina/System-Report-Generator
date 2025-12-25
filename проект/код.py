import platform
import psutil
import socket
import datetime
import json
from typing import Dict, List, Any

class SystemReport:
    def __init__(self, fmt: str = "text"):
        self.fmt = fmt
        self.info = {}
        self.time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def collect(self) -> Dict[str, Any]:
        self.info = {
            "time": self.time,
            "platform": self._platform(),
            "cpu": self._cpu(),
            "memory": self._memory(),
            "disks": self._disks(),
            "network": self._network(),
            "processes": self._processes(),
            "users": self._users(),
            "boot": self._boot(),
            "sensors": self._sensors()
        }
        return self.info
    
    def _platform(self) -> Dict[str, str]:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "host": socket.gethostname(),
            "ip": socket.gethostbyname(socket.gethostname())
        }
    
    def _cpu(self) -> Dict[str, Any]:
        freq = psutil.cpu_freq()
        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "freq": f"{freq.current:.0f} MHz" if freq else "N/A",
            "usage": psutil.cpu_percent(interval=0.5),
            "per_cpu": psutil.cpu_percent(interval=0.5, percpu=True)
        }
    
    def _memory(self) -> Dict[str, Any]:
        vmem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_ram": f"{vmem.total / (1024**3):.1f} GB",
            "used_ram": f"{vmem.used / (1024**3):.1f} GB",
            "ram_percent": vmem.percent,
            "swap": f"{swap.used / (1024**3):.1f}/{swap.total / (1024**3):.1f} GB"
        }
    
    def _disks(self) -> List[Dict[str, Any]]:
        disks = []
        for part in psutil.disk_partitions():
            try:
                use = psutil.disk_usage(part.mountpoint)
                disk_info = {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": f"{use.total / (1024**3):.1f} GB",
                    "used": f"{use.used / (1024**3):.1f} GB",
                    "free": f"{use.free / (1024**3):.1f} GB",
                    "percent": use.percent
                }
                
                try:
                    io = psutil.disk_io_counters(perdisk=True).get(part.device.replace("\\", "").replace("/", ""), None)
                    if io:
                        disk_info["read_bytes"] = f"{io.read_bytes / (1024**2):.1f} MB"
                        disk_info["write_bytes"] = f"{io.write_bytes / (1024**2):.1f} MB"
                except:
                    pass
                    
                disks.append(disk_info)
            except (PermissionError, OSError):
                continue
        return disks
    
    def _network(self) -> Dict[str, Any]:
        io = psutil.net_io_counters()
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        interfaces = {}
        for iface, addrs in net_if_addrs.items():
            ip_addresses = []
            mac_address = None
            
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip_addresses.append(f"IPv4: {addr.address}/{addr.netmask}")
                elif addr.family == socket.AF_INET6:
                    ip_addresses.append(f"IPv6: {addr.address}")
                elif addr.family == psutil.AF_LINK:
                    mac_address = addr.address
            
            stats = {}
            if iface in net_if_stats:
                stat = net_if_stats[iface]
                stats = {
                    "is_up": "UP" if stat.isup else "DOWN",
                    "speed": f"{stat.speed} Mbps" if stat.speed > 0 else "N/A",
                    "mtu": stat.mtu
                }
            
            interfaces[iface] = {
                "ip_addresses": ip_addresses,
                "mac": mac_address,
                "stats": stats
            }
        
        return {
            "bytes_sent": f"{io.bytes_sent / (1024**2):.1f} MB",
            "bytes_recv": f"{io.bytes_recv / (1024**2):.1f} MB",
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "interfaces": interfaces
        }
    
    def _processes(self) -> List[Dict[str, Any]]:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                info['memory_mb'] = psutil.Process(p.info['pid']).memory_info().rss / (1024**2)
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        return procs[:8]
    
    def _users(self) -> List[Dict[str, Any]]:
        users = []
        for user in psutil.users():
            users.append({
                "name": user.name,
                "host": user.host,
                "started": datetime.datetime.fromtimestamp(user.started).strftime("%H:%M:%S")
            })
        return users
    
    def _boot(self) -> str:
        return datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    
    def _sensors(self) -> Dict[str, Any]:
        try:
            temps = psutil.sensors_temperatures()
            sensors = {}
            if temps:
                for name, entries in temps.items():
                    sensors[name] = [{"current": entry.current} for entry in entries[:2]]
            return sensors
        except AttributeError:
            return {"info": "N/A"}
    
    def text_report(self) -> str:
        report = [
            "=" * 60,
            f"СИСТЕМНЫЙ ОТЧЕТ - {self.time}",
            "=" * 60
        ]
        
        report.extend([
            "\nПЛАТФОРМА:",
            "-" * 40,
            f"Система: {self.info['platform']['system']} {self.info['platform']['release']}",
            f"Версия: {self.info['platform']['version']}",
            f"Хост: {self.info['platform']['host']}",
            f"IP-адрес: {self.info['platform']['ip']}"
        ])
        
        cpu = self.info['cpu']
        report.extend([
            "\nПРОЦЕССОР:",
            "-" * 40,
            f"Ядра: {cpu['physical_cores']} физических, {cpu['logical_cores']} логических",
            f"Частота: {cpu['freq']}",
            f"Загрузка: {cpu['usage']}%",
            f"По ядрам: {', '.join([f'{p}%' for p in cpu['per_cpu']])}"
        ])
        
        mem = self.info['memory']
        report.extend([
            "\nПАМЯТЬ:",
            "-" * 40,
            f"ОЗУ: {mem['used_ram']} / {mem['total_ram']} ({mem['ram_percent']}%)",
            f"SWAP: {mem['swap']}"
        ])
        
        report.extend(["\nДИСКОВЫЕ НАКОПИТЕЛИ:", "-" * 40])
        for i, disk in enumerate(self.info['disks'], 1):
            disk_info = [
                f"{i}. {disk['device']} → {disk['mountpoint']}",
                f"   Тип: {disk['fstype']}, Всего: {disk['total']}",
                f"   Использовано: {disk['used']} ({disk['percent']}%), Свободно: {disk['free']}"
            ]
            if 'read_bytes' in disk:
                disk_info.append(f"   Чтение: {disk['read_bytes']}, Запись: {disk['write_bytes']}")
            report.extend(disk_info)
        
        net = self.info['network']
        report.extend([
            "\nСЕТЕВЫЕ ИНТЕРФЕЙСЫ:",
            "-" * 40,
            f"Отправлено: {net['bytes_sent']}, Получено: {net['bytes_recv']}",
            f"Пакеты: отправлено {net['packets_sent']}, получено {net['packets_recv']}"
        ])
        
        for iface, info in net['interfaces'].items():
            if info['ip_addresses']:
                report.append(f"\n{iface}:")
                if info['mac']:
                    report.append(f"  MAC: {info['mac']}")
                for ip in info['ip_addresses'][:2]:  # Показываем первые 2 адреса
                    report.append(f"  {ip}")
                if info['stats']:
                    report.append(f"  Статус: {info['stats']['is_up']}, "
                                 f"Скорость: {info['stats']['speed']}")
        
        report.extend(["\nТОП-8 ПРОЦЕССОВ:", "-" * 40])
        for i, proc in enumerate(self.info['processes'], 1):
            report.append(f"{i}. {proc['name'][:20]:20} "
                         f"PID:{proc['pid']:6} "
                         f"CPU:{proc['cpu_percent']:5.1f}% "
                         f"MEM:{proc['memory_percent']:5.1f}%")
        
        if self.info['users']:
            report.extend(["\nАКТИВНЫЕ ПОЛЬЗОВАТЕЛИ:", "-" * 40])
            for user in self.info['users']:
                report.append(f"{user['name']} с {user['host']} (с {user['started']})")
        
        report.extend([
            f"\nВРЕМЯ ЗАГРУЗКИ: {self.info['boot']}",
            "=" * 60
        ])
        
        return "\n".join(report)
    
    def json_report(self) -> str:
        return json.dumps(self.info, indent=2, default=str)
    
    def save(self, fname: str = None) -> str:
        if not fname:
            fname = f"system_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        fname += ".json" if self.fmt == "json" else ".txt"
        content = self.json_report() if self.fmt == "json" else self.text_report()
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        return fname

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Генератор системных отчетов")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Формат отчета (text или json)")
    parser.add_argument("--output", "-o", help="Имя выходного файла")
    parser.add_argument("--print", "-p", action="store_true",
                       help="Вывести отчет в консоль")
    
    args = parser.parse_args()
    
    try:
        report = SystemReport(args.format)
        report.collect()
        
        if args.print:
            print(report.json_report() if args.format == "json" else report.text_report())
        
        if args.output or not args.print:
            fname = report.save(args.output)
            print(f"Отчет сохранен: {fname}")
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
