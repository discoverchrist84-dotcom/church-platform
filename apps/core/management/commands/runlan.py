"""Run the development server so phones and other computers can open it.

    python manage.py runlan            # port 8000
    python manage.py runlan 8080

Works on home/office Wi-Fi *and* on a phone hotspot (either your phone shares its hotspot and the
computer joins it, or the computer shares its own hotspot and the phone joins that).
"""
import ipaddress
import os
import socket

from django.core.management import call_command
from django.core.management.base import BaseCommand


def _routed_ip() -> str | None:
    """The address on the network the computer uses for the internet (no traffic is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def private_ips() -> list[str]:
    """Every private IPv4 address of this computer, best guess first.

    A computer can have several (Wi-Fi, Ethernet, VPN, a hotspot it hosts), and only one of them is
    on the network your phone joined, so we list them all.
    """
    found = []
    routed = _routed_ip()
    if routed:
        found.append(routed)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(info[4][0])
    except OSError:
        pass
    out = []
    for ip in found:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if addr.is_loopback or addr.is_link_local or not addr.is_private or ip in out:
            continue
        out.append(ip)
    return out


def describe(ip: str) -> str:
    if ip.startswith("192.168.137."):
        return "this computer's own Windows Mobile Hotspot: use this if the phone joined the computer's hotspot"
    if ip.startswith("172.20.10."):
        return "an iPhone hotspot the computer joined"
    if ip.startswith("192.168.43.") or ip.startswith("192.168.49."):
        return "an Android phone hotspot the computer joined"
    return "your Wi-Fi / network"


class Command(BaseCommand):
    help = "Run the dev server for your phone: on Wi-Fi or a hotspot. Prints the address(es) to open."

    def add_arguments(self, parser):
        parser.add_argument("port", nargs="?", default="8000")

    def handle(self, *args, **opts):
        port = opts["port"]
        if os.environ.get("RUN_MAIN") == "true":  # the auto-reloader's child process: don't print twice
            return call_command("runserver", f"0.0.0.0:{port}")
        ips = private_ips()
        out = self.stdout.write
        out(self.style.SUCCESS(f"\n  On this computer:  http://localhost:{port}"))
        if ips:
            out(self.style.SUCCESS("  On your phone (open ONE of these in the phone's browser):"))
            for ip in ips:
                out(self.style.SUCCESS(f"      http://{ip}:{port}") + f"   <- {describe(ip)}")
        else:
            out(self.style.WARNING("  No network found. Connect to Wi-Fi or a hotspot first."))
        out("\n  Tip: the phone and computer must be on the SAME network (same Wi-Fi or same hotspot).")
        out("  Page won't load? Run scripts\\allow_dev_firewall.ps1 once as Administrator.")
        out("  Development only: plain HTTP, so use test data.\n")
        call_command("runserver", f"0.0.0.0:{port}")
