qemu-system-riscv64 -M virt -cpu rv64 -m 1G -nographic -bios none -kernel .\tftp\u-boot.bin -netdev tap,id=net0,ifname=tap0,script=no,downscript=no -device virtio-net-device,netdev=net0
