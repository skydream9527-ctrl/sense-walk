#!/usr/bin/env python3
"""SW-019 模拟器前后对照测量（gfxinfo）。用法见 docs/collaboration/evidence/H-SW-019-R1/README。

每个 APK 执行相同脚本：
  A. 虚走会话入场：MODE 页点「开始」前 reset gfxinfo，入场后 2s 读 framestats →
     入场帧窗口内最长单帧（原实现在此帧内同步解码五张图层）。
  B. 实走会话入场（debug stub）：同上；原实现在此帧内另有 RealWalkVisualCache.runBlocking。
  C. 虚走行走 30s：reset → 摇杆长拖 30s → gfxinfo 汇总（总帧/卡顿帧%/P50/P90/P95/P99）。
"""
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

SERIAL = "emulator-5554"
PKG = "com.sensewalk.app"
ADB = ["adb", "-s", SERIAL]


def adb(*args, check=True, timeout=120):
    return subprocess.run(ADB + list(args), capture_output=True, text=True, check=check, timeout=timeout).stdout


def shell(cmd, timeout=120):
    return adb("shell", cmd, timeout=timeout)


def ui_nodes():
    shell("uiautomator dump /sdcard/ui.xml")
    xml = shell("cat /sdcard/ui.xml")
    root = ET.fromstring(xml)
    out = []
    for n in root.iter("node"):
        b = n.get("bounds") or ""
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({
            "text": n.get("text") or "",
            "desc": n.get("content-desc") or "",
            "cx": (x1 + x2) // 2,
            "cy": (y1 + y2) // 2,
            "clickable": n.get("clickable") == "true",
        })
    return out


def find(substr, nodes=None):
    nodes = nodes if nodes is not None else ui_nodes()
    # 先精确匹配（避免「放弃这段路」命中标题「要放弃这段路吗？」），再子串匹配
    for n in nodes:
        if substr == n["text"] or substr == n["desc"]:
            return n
    for n in nodes:
        if substr in n["text"] or substr in n["desc"]:
            return n
    return None


def wait_for(substr, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        n = find(substr)
        if n:
            return n
        time.sleep(0.5)
    raise RuntimeError(f"UI element containing {substr!r} not found within {timeout}s")


def tap(n):
    # Compose 卡片用带按压时长的 swipe 比 tap 可靠（见本地环境记录）
    shell(f"input swipe {n['cx']} {n['cy']} {n['cx']} {n['cy']} 150")


def gfx_reset():
    shell(f"dumpsys gfxinfo {PKG} reset")


def gfx_summary():
    txt = shell(f"dumpsys gfxinfo {PKG}")
    keys = [
        "Total frames rendered", "Janky frames", "50th percentile", "90th percentile",
        "95th percentile", "99th percentile", "Number Missed Vsync", "Number Slow UI thread",
        "Number Slow bitmap uploads", "Number Slow issue draw commands", "Number Frame deadline missed",
    ]
    res = {}
    for line in txt.splitlines():
        for k in keys:
            if line.strip().startswith(k):
                res[k] = line.split(":", 1)[1].strip()
    return res


def gfx_framestats():
    """返回最近窗口内每帧总时长 ms（FrameCompleted - IntendedVsync），ring buffer ≤ ~120 帧"""
    txt = shell(f"dumpsys gfxinfo {PKG} framestats")
    rows = []
    in_data = False
    header = None
    for line in txt.splitlines():
        if line.startswith("---PROFILEDATA---"):
            in_data = not in_data
            header = None
            continue
        if not in_data:
            continue
        parts = line.strip().split(",")
        if header is None:
            header = parts
            continue
        if len(parts) < len(header) - 1:
            continue
        try:
            rec = {header[i]: int(parts[i]) for i in range(min(len(header), len(parts))) if parts[i] != ""}
        except ValueError:
            continue
        if "IntendedVsync" in rec and "FrameCompleted" in rec and rec["IntendedVsync"] > 0:
            rows.append((rec["FrameCompleted"] - rec["IntendedVsync"]) / 1e6)
    return rows


def describe(frames):
    if not frames:
        return {"frames": 0}
    s = sorted(frames)
    return {
        "frames": len(s),
        "max_ms": round(s[-1], 1),
        "over_16_7ms": sum(1 for f in s if f > 16.7),
        "over_50ms": sum(1 for f in s if f > 50),
        "over_100ms": sum(1 for f in s if f > 100),
        "top3_ms": [round(x, 1) for x in s[-3:][::-1]],
    }


def launch_home():
    shell(f"am force-stop {PKG}")
    time.sleep(0.8)
    shell(f"am start -W -n {PKG}/.MainActivity")
    wait_for("下一步")  # 首页森林卡/按钮已渲染


def go_mode_page():
    """首页 → 选「森林」卡 → 「下一步 · 怎么走」→ MODE 页（判据：出现「虚走 · 手机上走」）"""
    tap(wait_for("森林，800"))
    time.sleep(0.5)
    tap(wait_for("下一步"))
    wait_for("虚走 · 手机上走")


def enter_session(mode_substr, ready_substr):
    """MODE 页：选模式卡 → 点「开始」。开始前 reset，入场后等 ready_substr 出现再读 framestats。"""
    tap(wait_for(mode_substr))
    time.sleep(0.6)
    start = wait_for("开始")
    gfx_reset()
    tap(start)
    wait_for(ready_substr, timeout=25)
    time.sleep(1.5)  # 让入场帧全部完成；0m 静止不再出帧
    frames = gfx_framestats()
    summary = gfx_summary()
    return {"entry": describe(frames), "summary": summary}


def walk_30s():
    """虚走：摇杆区（下 45%）长拖 30s；dumpsys 不打断手势（避免 uiautomator dump）"""
    size = shell("wm size").strip().split()[-1]
    w, h = map(int, size.split("x"))
    y = int(h * 0.80)
    x1, x2 = int(w * 0.30), int(w * 0.30) + 900
    gfx_reset()
    subprocess.run(ADB + ["shell", f"input swipe {x1} {y} {x2} {y} 30000"], capture_output=True, timeout=60)
    time.sleep(0.5)
    return gfx_summary()


def leave_to_result():
    """返回 → 确认框「放弃这段路」→ 结果页；返回结果页「这次走了 N m」文案"""
    shell("input keyevent KEYCODE_BACK")
    tap(wait_for("放弃这段路"))
    wait_for("再走一次", timeout=20)
    n = find("这次走了")
    return n["text"] if n else ""


def walk_again_to_mode():
    """结果页「再走一次」→ 同场景 MODE 页（进程保持热态）"""
    tap(wait_for("再走一次"))
    wait_for("虚走 · 手机上走")


def device_info():
    return {
        "model": shell("getprop ro.product.model").strip(),
        "sdk": shell("getprop ro.build.version.sdk").strip(),
        "release": shell("getprop ro.build.version.release").strip(),
        "size": shell("wm size").strip(),
        "density": shell("wm density").strip(),
        "gpu": shell("getprop ro.hardware.egl").strip(),
        "refresh": shell("dumpsys display | grep -oE 'fps=[0-9.]+' | head -1").strip(),
    }


def install(apk):
    subprocess.run(ADB + ["uninstall", PKG], capture_output=True)
    out = adb("install", "-r", apk)
    assert "Success" in out, out
    shell(f"pm grant {PKG} android.permission.ACTIVITY_RECOGNITION")
    shell("settings put global sensewalk_debug_stub 1")


VIRTUAL = "虚走 · 手机上走"
REAL = "实走 · 出门走"
READY = "轻触查看米数"


def run(apk, label, warm_repeats=3):
    print(f"\n===== {label}: {apk} =====", flush=True)
    install(apk)
    results = {"label": label, "apk": apk}

    # 冷进程：虚走入场（含 JIT/类加载噪声，单独报告）
    launch_home()
    go_mode_page()
    results["virtual_entry_cold"] = enter_session(VIRTUAL, READY)
    print(f"[virtual entry cold] {results['virtual_entry_cold']}", flush=True)

    # 行走 30s（同一会话内）
    results["walk30s"] = walk_30s()
    results["walk30s"]["result_text"] = leave_to_result()
    print(f"[walk 30s] {results['walk30s']}", flush=True)

    # 热进程：虚走入场 ×N
    results["virtual_entry_warm"] = []
    for i in range(warm_repeats):
        walk_again_to_mode()
        r = enter_session(VIRTUAL, READY)
        leave_to_result()
        print(f"[virtual entry warm #{i+1}] {r}", flush=True)
        results["virtual_entry_warm"].append(r)

    # 热进程：实走入场 ×N（debug stub；原实现在此处 runBlocking）
    results["real_entry_warm"] = []
    for i in range(warm_repeats):
        walk_again_to_mode()
        r = enter_session(REAL, READY)
        leave_to_result()
        print(f"[real entry warm #{i+1}] {r}", flush=True)
        results["real_entry_warm"].append(r)

    # 冷进程：实走入场
    launch_home()
    go_mode_page()
    results["real_entry_cold"] = enter_session(REAL, READY)
    leave_to_result()
    print(f"[real entry cold] {results['real_entry_cold']}", flush=True)
    return results


if __name__ == "__main__":
    import json
    print("device:", json.dumps(device_info(), ensure_ascii=False))
    out = []
    for apk, label in zip(sys.argv[1::2], sys.argv[2::2]):
        out.append(run(apk, label))
    print("\n===== JSON =====")
    print(json.dumps(out, ensure_ascii=False, indent=1))
