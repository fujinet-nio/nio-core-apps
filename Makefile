TARGETS := msdos atari linux amiga
BOOT_IMAGE_TARGETS := msdos atari
DEFAULT_TARGET := $(if $(TARGET),$(TARGET),all-targets)
AMIGA_PROFILES := wb13 wb31 wb32
AMIGA_PROFILE ?=

AMIGA_CRT_wb13 := nix13
AMIGA_CRT_wb31 := clib2
AMIGA_CRT_wb32 := clib2

.PHONY: all all-targets clean disk disk-all boot-disk boot-disk-all install-boot-disk test-hsioflip test-c64 c64 $(TARGETS)

HOSTCC ?= cc
FUJINET_NIO_LIB ?= ../fujinet-nio-lib
all: $(DEFAULT_TARGET)

test-hsioflip:
	mkdir -p build/tests
	$(HOSTCC) -std=c99 -Wall -Wextra -Werror -DHSIOFLIP_TEST -D__fastcall__= \
	    -I$(FUJINET_NIO_LIB)/include apps/platform/atari/hsioflip.c tests/hsioflip_test.c -o build/tests/hsioflip-test
	build/tests/hsioflip-test

# The C64 boot disk's image writer, and the demo's generators.
test-c64:
	python3 -m unittest discover -s boot-disk/scripts -p 'test_create_d64.py'
	python3 -m unittest discover -s apps/platform/c64/fujidemo/tools -p 'test_*.py'

msdos atari linux:
	$(MAKE) -f makefiles/build.mk TARGET=$@

# The utilities aren't built for the C64 yet (makefiles/build.mk).
c64:
	$(MAKE) -f makefiles/build.mk TARGET=$@

# Amiga executables are always profile-qualified.  Supplying AMIGA_PROFILE
# builds one profile; plain `make amiga` produces all supported variants.
amiga:
ifeq ($(AMIGA_PROFILE),)
	@for profile in $(AMIGA_PROFILES); do \
		$(MAKE) -C ../fujinet-nio-driver amiga AMIGA_PROFILE=$$profile || exit $$?; \
		$(MAKE) -f makefiles/build.mk TARGET=amiga \
			TARGET_BUILD_DIR=build/amiga/$$profile \
			AMIGA_CRT=$$(if [ "$$profile" = wb13 ]; then echo nix13; else echo clib2; fi) \
			AMIGA_WB13=$$(if [ "$$profile" = wb13 ]; then echo 1; else echo 0; fi) \
			FUJINET_NIO_DRIVER_BUILD=../fujinet-nio-driver/build/amiga/$$profile || exit $$?; \
	done
else
	$(MAKE) -C ../fujinet-nio-driver amiga AMIGA_PROFILE=$(AMIGA_PROFILE)
	$(MAKE) -f makefiles/build.mk TARGET=amiga \
		TARGET_BUILD_DIR=build/amiga/$(AMIGA_PROFILE) \
		AMIGA_CRT=$(AMIGA_CRT_$(AMIGA_PROFILE)) \
		AMIGA_WB13=$(if $(filter wb13,$(AMIGA_PROFILE)),1,0) \
		FUJINET_NIO_DRIVER_BUILD=../fujinet-nio-driver/build/amiga/$(AMIGA_PROFILE)
endif

all-targets: $(TARGETS)

disk:
	$(MAKE) -f makefiles/build.mk TARGET=$(if $(TARGET),$(TARGET),msdos) disk

disk-all:
	@for target in $(TARGETS); do \
		$(MAKE) -f makefiles/build.mk TARGET=$$target disk; \
	done

boot-disk:
	$(MAKE) -f makefiles/build.mk TARGET=$(if $(TARGET),$(TARGET),msdos) boot-disk

boot-disk-all:
	@for target in $(BOOT_IMAGE_TARGETS); do \
		$(MAKE) -f makefiles/build.mk TARGET=$$target boot-disk; \
	done

install-boot-disk:
	$(MAKE) -f makefiles/build.mk TARGET=$(if $(TARGET),$(TARGET),msdos) install-boot-disk

clean:
	rm -rf build
