# Imagen AI Go SDK

Idiomatic, zero-dependency Go client for the [Imagen AI](https://imagen-ai.com) photo-editing API. Standard library only; context-first; safe for concurrent use.

```bash
go get github.com/imagenai/imagen-ai-sdk/sdks/go
```

```go
import imagen "github.com/imagenai/imagen-ai-sdk/sdks/go"
```

## Quick start

One call runs the whole workflow — create project, upload, edit, wait, (optionally) export and download:

```go
client, err := imagen.NewClient(os.Getenv("IMAGEN_API_KEY"))
if err != nil {
    log.Fatal(err)
}

opts := imagen.EditOptions{}
opts.PortraitCrop = imagen.Bool(true)
opts.SmoothSkin = imagen.Bool(true)

result, err := client.QuickEdit(context.Background(), imagen.QuickEditParams{
    ProfileKey:      1,
    ImagePaths:      []string{"photo1.dng", "photo2.dng"},
    PhotographyType: imagen.PhotographyTypeWedding,
    EditOptions:     opts,
    Export:          true,
    Download:        true,
    DownloadDir:     "out",
})
if err != nil {
    log.Fatal(err)
}
fmt.Println("project:", result.ProjectUUID)
fmt.Println("edited XMPs:", result.DownloadedFiles)
// With Export+Download, exported JPEGs land in ExportDownloadDir
// (defaults to DownloadDir/"exported").
fmt.Println("exported JPEGs:", result.ExportedFiles)
```

## Step by step

```go
uuid, _ := client.CreateProject(ctx, "My Photos")

summary, _ := client.UploadImages(ctx, uuid, paths, &imagen.UploadOptions{
    CalculateMD5: true,
    Progress: func(done, total int, name string) {
        fmt.Printf("uploaded %d/%d: %s\n", done, total, name)
    },
})
fmt.Printf("%d/%d uploaded\n", summary.Successful, summary.Total)

edit := imagen.EditRequest{ProfileKey: 1, PhotographyType: imagen.PhotographyTypePortraits}
edit.Crop = imagen.Bool(true)
if err := client.EditAndWait(ctx, uuid, edit, nil); err != nil {
    log.Fatal(err)
}

links, _ := client.GetDownloadLinks(ctx, uuid)               // XMP sidecars
files, _ := client.DownloadFiles(ctx, links.FilesList, "out", nil)
```

## Options

Optional edit toggles are pointers so "unset" is distinct from "false" and is
omitted from the request. Use the `Bool`, `Int`, and `String` helpers. The SDK
validates the crop/straighten mutual-exclusivity rules client-side.

Configure the client with functional options:

```go
client, _ := imagen.NewClient(key,
    imagen.WithBaseURL("https://staging.imagen-ai.com/v1"),
    imagen.WithHTTPClient(&http.Client{Timeout: 2 * time.Minute}),
    imagen.WithMaxConcurrency(20),
    imagen.WithLogger(imagen.StdLogger(log.Default())),
)
```

## Image-to-image (I2I)

`UploadI2IImages` routes each file by size automatically: small files are batched
into single PUTs, large files use S3 multipart upload (64 MB parts by default).
I2I editing reports status on the project object — `WaitForI2ICompletion` polls it
(`Pending → In Progress → Completed/Failed`), returns the result links on success,
and errors (`ErrProject`) on failure. You can also supply a `callback_url`:

```go
uuid, _ := client.CreateI2IProject(ctx, "shoot")
client.UploadI2IImages(ctx, uuid, paths, nil)
client.StartI2IEditing(ctx, uuid, &imagen.I2IEditOptions{HDRMerge: imagen.Bool(true)})
links, _ := client.WaitForI2ICompletion(ctx, uuid, nil)
```

## Enhancement, copilot, finalize

```go
tools, _ := client.GetAITools(ctx, uuid, imagen.ProjectSourceRegular)
client.EnhanceImage(ctx, uuid, "photo.dng", imagen.EnhanceRequest{
    ToolID: tools.Prompts[0].EnhancementType, ProjectSource: imagen.ProjectSourceRegular,
})
client.Copilot(ctx, uuid, "photo.dng", imagen.CopilotRequest{
    Instruction: "warm up the highlights", ProjectSource: imagen.ProjectSourceRegular,
})
downloads, _ := client.Finalize(ctx, uuid, imagen.ProjectSourceRegular)
```

## Errors

Non-2xx responses return `*APIError`. Well-known statuses wrap sentinels:

```go
if errors.Is(err, imagen.ErrUnauthorized) { /* bad/expired key */ }

var apiErr *imagen.APIError
if errors.As(err, &apiErr) {
    fmt.Println(apiErr.StatusCode, apiErr.Message)
}
```

Upload and download failures wrap `ErrUpload` / `ErrDownload`; a failed edit job
wraps `ErrProject`.
