package imagen

import (
	"fmt"
	"path/filepath"
	"strings"
)

// RAWExtensions are the supported RAW file extensions (lowercase, with dot). This
// set is kept identical to the reference Python/Node SDKs so all clients accept
// and skip exactly the same files.
var RAWExtensions = map[string]bool{
	".dng": true, ".nef": true, ".cr2": true, ".arw": true, ".nrw": true,
	".crw": true, ".srf": true, ".sr2": true, ".orf": true, ".raw": true,
	".rw2": true, ".raf": true, ".ptx": true, ".pef": true, ".rwl": true,
	".srw": true, ".cr3": true, ".3fr": true, ".fff": true,
}

// JPGExtensions are the supported JPEG file extensions (lowercase, with dot).
var JPGExtensions = map[string]bool{
	".jpg": true, ".jpeg": true,
}

// SupportedExtension reports whether path has a RAW or JPG extension.
func SupportedExtension(path string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	return RAWExtensions[ext] || JPGExtensions[ext]
}

// imageTypeForExt returns "RAW", "JPG", or "" for an unsupported extension.
func imageTypeForExt(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch {
	case RAWExtensions[ext]:
		return "RAW"
	case JPGExtensions[ext]:
		return "JPG"
	default:
		return ""
	}
}

// checkUniqueBaseNames errors if two of the given paths share a base name.
// Uploads are keyed by base name, so same-named files from different directories
// would collide (one upload link, one result entry, last write wins).
func checkUniqueBaseNames(paths []string) error {
	seen := make(map[string]bool, len(paths))
	for _, p := range paths {
		b := filepath.Base(p)
		if seen[b] {
			return fmt.Errorf("imagen: duplicate file name %q: files are uploaded by base name, so inputs with the same name from different directories collide", b)
		}
		seen[b] = true
	}
	return nil
}

// CheckFilesMatchProfileType verifies that every file's image type matches the
// profile's ImageType (RAW or JPG). It returns an error listing the mismatches.
// Profiles with an empty ImageType accept any supported file.
func CheckFilesMatchProfileType(profile Profile, paths []string) error {
	if profile.ImageType == "" {
		return nil
	}
	want := strings.ToUpper(profile.ImageType)
	var mismatched []string
	for _, p := range paths {
		if imageTypeForExt(p) != want {
			mismatched = append(mismatched, filepath.Base(p))
		}
	}
	if len(mismatched) > 0 {
		return fmt.Errorf("imagen: profile expects %s files but these do not match: %s",
			want, strings.Join(mismatched, ", "))
	}
	return nil
}
