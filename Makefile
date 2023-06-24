BUILD_DIR = ./build
SOURCE_FILES = $(wildcard *.py)
VERSION := $(shell git describe --tags --abbrev=0)
BUILD_FILE = $(BUILD_DIR)/svnconnector_$(VERSION).zip

.PHONY: clean

all: build

clean:
	rm -rf $(BUILD_DIR)

build: $(SOURCE_FILES)
	mkdir -p $(BUILD_DIR)
	zip -u $(BUILD_FILE) $(SOURCE_FILES)