qemu-system-riscv64 -M virt -cpu rv64 -m 1G -nographic -bios default -kernel .\PrintRegisterHarness\kernel.bin -netdev user,id=net0,tftp=.\tftp,bootfile=boot.scr -device virtio-net-device,netdev=net0
