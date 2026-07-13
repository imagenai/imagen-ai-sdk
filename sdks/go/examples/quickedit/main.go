// Command quickedit runs the full Imagen AI editing workflow on a folder of
// images using the one-call QuickEdit helper.
//
// Usage:
//
//	IMAGEN_API_KEY=... go run ./examples/quickedit -profile 1 -dir ./photos -out ./edited
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	imagen "github.com/imagenai/imagen-ai-sdk/sdks/go"
)

func main() {
	profile := flag.Int("profile", 0, "profile key (required)")
	dir := flag.String("dir", ".", "directory of images to edit")
	out := flag.String("out", "edited", "download directory for results")
	export := flag.Bool("export", true, "export to JPEG in addition to XMP")
	flag.Parse()

	apiKey := os.Getenv("IMAGEN_API_KEY")
	if apiKey == "" || *profile == 0 {
		log.Fatal("set IMAGEN_API_KEY and -profile")
	}

	paths, err := imagePaths(*dir)
	if err != nil {
		log.Fatal(err)
	}
	if len(paths) == 0 {
		log.Fatalf("no supported images in %s", *dir)
	}

	client, err := imagen.NewClient(apiKey)
	if err != nil {
		log.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	result, err := client.QuickEdit(ctx, imagen.QuickEditParams{
		ProfileKey:  *profile,
		ImagePaths:  paths,
		Export:      *export,
		Download:    true,
		DownloadDir: *out,
		Upload: &imagen.UploadOptions{
			Progress: func(done, total int, name string) {
				fmt.Printf("  uploaded %d/%d: %s\n", done, total, name)
			},
		},
	})
	if err != nil {
		log.Fatalf("QuickEdit failed (project %s): %v", result.ProjectUUID, err)
	}

	fmt.Printf("done: project %s, %d XMPs downloaded to %s\n",
		result.ProjectUUID, len(result.DownloadedFiles), *out)
	if *export {
		fmt.Printf("  %d exported JPEGs\n", len(result.ExportedFiles))
	}
}

// imagePaths returns supported image files in dir (non-recursive).
func imagePaths(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var paths []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		p := filepath.Join(dir, e.Name())
		if imagen.SupportedExtension(p) {
			paths = append(paths, p)
		}
	}
	return paths, nil
}
