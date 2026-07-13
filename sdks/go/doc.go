// Package imagen is the Go SDK for the Imagen AI photo-editing API.
//
// The SDK mirrors the Imagen AI workflow:
//
//  1. Create a client with an API key.
//  2. Create a project.
//  3. Upload images to presigned S3 URLs (concurrently).
//  4. Start editing and poll status until complete.
//  5. Download results (XMP or exported JPEGs).
//
// Every method takes a context.Context and returns typed values and errors.
// The client is safe for concurrent use by multiple goroutines.
//
// Quick start:
//
//	client, err := imagen.NewClient("your_api_key")
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	uuid, err := client.CreateProject(ctx, "My Photos")
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	if _, err := client.UploadImages(ctx, uuid, []string{"photo1.dng"}, nil); err != nil {
//		log.Fatal(err)
//	}
//
//	edit := imagen.EditRequest{ProfileKey: 1, PhotographyType: imagen.PhotographyTypePortraits}
//	edit.Crop = imagen.Bool(true)
//	if err := client.EditAndWait(ctx, uuid, edit, nil); err != nil {
//		log.Fatal(err)
//	}
//
//	links, err := client.GetDownloadLinks(ctx, uuid)
//	if err != nil {
//		log.Fatal(err)
//	}
//	files, err := client.DownloadFiles(ctx, links.FilesList, "out", nil)
//
// The one-call convenience QuickEdit runs the whole flow end to end.
//
// The SDK has no external dependencies beyond the Go standard library.
package imagen
