# Raster API with TiTiler

A containerized raster data processing and serving solution using TiTiler for dynamic tile generation and raster file management.

## Overview

This project consists of a raster API service that saves raster files to a shared storage location, integrated with a TiTiler container that serves these raster files as dynamic tiles. The system is designed for efficient raster data processing and visualization.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Raster API    │───▶│  Shared Storage  │◀───│    TiTiler      │
│   (Save/Delete) │    │   (RASTER_ROOT)  │    │  (Tile Server)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                        /home/jazi/Work/zarrin/raster
```

## Components

### 1. TiTiler Container
- **Purpose**: Serves raster files as dynamic tiles
- **Base Image**: `python:3.12.5-alpine3.20`
- **Port**: 8008
- **Features**:
  - Dynamic tile generation
  - Multiple raster format support
  - RESTful API endpoints

### 2. Shared Storage
- **Path**: `RASTER_ROOT (.env)`
- **Purpose**: Centralized storage for raster files
- **Access**: Mounted as volume in TiTiler container at `/app/raster`

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
RASTER_ROOT=<...>
```

### Docker Configuration

The system uses Docker Compose for orchestration with the following key configurations:

#### TiTiler Service
- **Container Name**: `zarrin_titiler`
- **Network**: `zarrinnet`
- **Volume Mount**: `${RASTER_ROOT}:/app/raster`
- **Health Check**: Automated endpoint monitoring
- **Restart Policy**: `unless-stopped`

## Prerequisites

- Docker and Docker Compose
- Sufficient disk space for raster file storage
- Network access for tile serving

### TiTiler API Endpoints

Once running, TiTiler will be available at `http://localhost:8008` with the following key endpoints:

- **Health Check**: `GET /`
- **Tile Endpoint**: `GET /cog/tiles/{z}/{x}/{y}?url=/app/raster/{filename}`
- **Info Endpoint**: `GET /cog/info?url=/app/raster/{filename}`
- **Statistics**: `GET /cog/statistics?url=/app/raster/{filename}`

### Raster File Management

Your raster API should save files to the `RASTER_ROOT` directory. Files saved here will be automatically accessible to the TiTiler service through the mounted volume.

Example workflow:
1. Raster API receives file upload
2. File is saved to `${RASTER_ROOT}/output_cog.tif`
3. TiTiler can immediately serve tiles from `/app/raster/output_cog.tif`

## File Structure

```
project/
├── .env                    # Environment configuration
├── docker-compose.yml     # Service orchestration
├── titiler/
│   ├── Dockerfile.dev     # TiTiler container definition
│   └── starttitiler.sh    # Startup script
└── README.md              # This file
```

1. **Container fails to start**
   - Check if port 8008 is available
   - Verify RASTER_ROOT directory exists and has proper permissions
   - Review logs: `docker-compose logs titiler`

2. **Files not accessible**
   - Ensure files are saved to the correct RASTER_ROOT path
   - Check volume mount configuration
   - Verify file permissions

3. **Health check failures**
   - Confirm TiTiler service is responding on port 8008
   - Check network connectivity
   - Review container logs for errors

### Logs and Debugging

```bash
# View real-time logs
docker-compose logs -f titiler

# Access container shell
docker exec -it zarrin_titiler sh

# Check mounted volumes
docker exec -it zarrin_titiler ls -la /app/raster
```


## Security Notes

- The TiTiler service runs as a non-root user (`titilerrunner`)
- Ensure proper file permissions on the RASTER_ROOT directory
- Consider implementing authentication for production deployments
- Review and secure network access as needed

