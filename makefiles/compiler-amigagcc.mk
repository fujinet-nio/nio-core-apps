CC := m68k-amigaos-gcc
AMIGA_CRT ?= clib2
# Headers/defines to compile against; defaults to the link runtime.  nix13 defines
# __KICK13__, so a 2.0+ build that links the nix13 startup (a bare system without
# a Workbench startup needs it; clib2 programs crash there) sets nix20 here.
AMIGA_COMPILE_CRT ?= $(AMIGA_CRT)
AMIGA_WB13 ?= 0
FUJINET_NIO_DRIVER_BUILD ?= ../fujinet-nio-driver/build/amiga

CFLAGS += -Wall -Wextra -O2 -std=c99
CFLAGS += -mcpu=68000 -msoft-float
# Select clib2 headers as well as its libraries. Compiling against newlib
# headers and linking with clib2 can leave newlib-only symbols unresolved.
CFLAGS += -mcrt=$(AMIGA_COMPILE_CRT)
CFLAGS += -I$(APP_INCLUDE_DIR)
CFLAGS += -I$(CONFIG_NIO_INCLUDE_DIR)
CFLAGS += -I$(PLATFORM_INCLUDE_DIR)
CFLAGS += -I$(NIO_INCLUDE_DIR)
CFLAGS += -I$(FUJINET_NIO_DRIVER_BUILD)/include
CFLAGS += -DFNSVC_LIST_MAX_PAYLOAD=$(FNSVC_LIST_MAX_PAYLOAD)
CFLAGS += -D__AMIGA__
ifeq ($(AMIGA_WB13),1)
CFLAGS += -D__KICK13__
endif

# Keep Amiga applications self-contained instead of requiring the optional
# mathieeedoubbas.library at process startup.
LDFLAGS += -mcpu=68000 -msoft-float -mcrt=$(AMIGA_CRT)
LDFLAGS += -L$(FUJINET_NIO_DRIVER_BUILD)/lib -lfujinet-amiga-disk

define compile_c
	$(CC) $(CFLAGS) -MMD -MF $(@:.o=.d) -c -o $@ $<
endef

define link_program
	$(CC) -o $@ $^ $(LDFLAGS) $(EXTRA_PROGRAM_LDFLAGS) -lamiga
endef
