// --- VARIABLES DE ESTADO LOCAL ---
let selectedImages = [];
let selectedCadFile = null;
let reportesList = [];

// Al iniciar el documento
document.addEventListener("DOMContentLoaded", () => {
    // Inicializar Lucide Icons
    lucide.createIcons();
    
    // Cargar historial de reportes inicial
    cargarHistorialReportes();
    
    // Configurar zonas Drag-and-Drop
    setupDragAndDrop("cad-drop-zone", "cad-file-input", handleCadFile);
    setupDragAndDrop("images-drop-zone", "images-file-input", handleImageFiles);
});

// --- SISTEMA DE PESTAÑAS (TABS) ---
function switchTab(tabId) {
    // Ocultar todas las pestañas
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
    
    // Mostrar pestaña seleccionada
    document.getElementById(`tab-${tabId}`).classList.add("active");
    document.getElementById(`btn-tab-${tabId}`).classList.add("active");
    
    // Si entramos al dashboard, recargamos el historial
    if (tabId === 'dashboard') {
        cargarHistorialReportes();
    }
}

// --- CONFIGURACIÓN DE DRAG & DROP ---
function setupDragAndDrop(zoneId, inputId, fileHandler) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    
    if (!zone || !input) return;
    
    // Prevenir comportamientos por defecto
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    
    // Clases en hover
    ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('dragover'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('dragover'), false);
    });
    
    // Al soltar el archivo
    zone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileHandler(files);
    });
}

// --- PROCESAMIENTO DE ARCHIVO CAD ---
function handleCadSelect(event) {
    const files = event.target.files;
    handleCadFile(files);
}

function handleCadFile(files) {
    if (files.length === 0) return;
    
    const file = files[0];
    const extension = file.name.split('.').pop().toLowerCase();
    
    if (extension !== 'dwg' && extension !== 'dxf') {
        alert("Por favor, sube solo archivos con formato .DWG o .DXF.");
        return;
    }
    
    selectedCadFile = file;
    
    // Actualizar vista previa CAD
    document.getElementById("cad-name").textContent = file.name;
    document.getElementById("cad-size").textContent = formatBytes(file.size);
    document.getElementById("cad-preview").classList.remove("hidden");
    document.getElementById("cad-drop-zone").classList.add("hidden");
}

function clearCadFile() {
    selectedCadFile = null;
    document.getElementById("cad-file-input").value = "";
    document.getElementById("cad-preview").classList.add("hidden");
    document.getElementById("cad-drop-zone").classList.remove("hidden");
}

// --- PROCESAMIENTO DE IMÁGENES ---
function handleImagesSelect(event) {
    const files = event.target.files;
    handleImageFiles(files);
}

function handleImageFiles(files) {
    if (files.length === 0) return;
    
    // Permitir un máximo de 6 imágenes
    const espacioDisponible = 6 - selectedImages.length;
    if (espacioDisponible <= 0) {
        alert("Ya has alcanzado el límite máximo de 6 imágenes de campo.");
        return;
    }
    
    const validFiles = Array.from(files).filter(file => {
        const type = file.type;
        return type === "image/png" || type === "image/jpeg" || type === "image/jpg";
    });
    
    if (validFiles.length !== files.length) {
        alert("Solo se permiten imágenes en formato PNG o JPG.");
    }
    
    const filesToLoad = validFiles.slice(0, espacioDisponible);
    
    filesToLoad.forEach(file => {
        selectedImages.push(file);
        
        // Crear preview local
        const reader = new FileReader();
        reader.onload = e => {
            renderImagePreviewCard(e.target.result, file.name, selectedImages.length - 1);
        };
        reader.readAsDataURL(file);
    });
}

function renderImagePreviewCard(src, name, index) {
    const grid = document.getElementById("images-preview-grid");
    
    const card = document.createElement("div");
    card.className = "image-preview-item";
    card.id = `img-preview-${index}`;
    card.innerHTML = `
        <img src="${src}" alt="${name}">
        <div class="image-overlay">
            <button type="button" class="btn-delete-img" onclick="removeImage(${index})">
                <i data-lucide="trash-2"></i>
            </button>
        </div>
    `;
    
    grid.appendChild(card);
    lucide.createIcons(); // Renderizar iconos Lucide
}

function removeImage(index) {
    // Remover del array en memoria
    selectedImages.splice(index, 1);
    
    // Limpiar grid de previews y volver a renderizar para recalcular índices
    const grid = document.getElementById("images-preview-grid");
    grid.innerHTML = "";
    
    selectedImages.forEach((file, idx) => {
        const reader = new FileReader();
        reader.onload = e => {
            renderImagePreviewCard(e.target.result, file.name, idx);
        };
        reader.readAsDataURL(file);
    });
    
    // Limpiar el input de archivos por seguridad
    document.getElementById("images-file-input").value = "";
}

// --- CARGAR HISTORIAL DESDE LA API ---
async function cargarHistorialReportes() {
    const listContainer = document.getElementById("reportes-list");
    
    try {
        const response = await fetch("/api/reportes");
        if (!response.ok) throw new Error("Error obteniendo reportes.");
        
        reportesList = await response.json();
        
        // Actualizar estadísticas rápidas
        document.getElementById("stat-total-files").textContent = reportesList.length;
        
        let totalSize = 0;
        reportesList.forEach(r => totalSize += r.size);
        document.getElementById("stat-storage-size").textContent = formatBytes(totalSize);
        
        // Renderizar tabla
        if (reportesList.length === 0) {
            listContainer.innerHTML = `
                <tr>
                    <td colspan="4" class="empty-state">
                        <i data-lucide="file-warning"></i>
                        <p>No se encontraron reportes guardados en archivos_salida/.</p>
                    </td>
                </tr>
            `;
            lucide.createIcons();
            return;
        }
        
        renderTableRows(reportesList);
        
    } catch (e) {
        listContainer.innerHTML = `
            <tr>
                <td colspan="4" class="empty-state" style="color: var(--accent-red)">
                    <i data-lucide="alert-triangle"></i>
                    <p>No se pudo conectar con el servidor local FastAPI. Asegúrate de que esté encendido.</p>
                </td>
            </tr>
        `;
        lucide.createIcons();
        console.error(e);
    }
}

function renderTableRows(items) {
    const listContainer = document.getElementById("reportes-list");
    listContainer.innerHTML = "";
    
    items.forEach(r => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>
                <div class="file-name-cell">
                    <i data-lucide="file-text" class="pdf-icon"></i>
                    <span>${r.name}</span>
                </div>
            </td>
            <td>${formatBytes(r.size)}</td>
            <td>${r.date}</td>
            <td class="actions-col">
                <div class="actions-btn-group">
                    <button class="btn-action" title="Previsualizar" onclick="previewReport('${r.name}')">
                        <i data-lucide="eye"></i>
                    </button>
                    <a class="btn-action" title="Descargar" href="/static/archivos_salida/${r.name}" download>
                        <i data-lucide="download"></i>
                    </a>
                    <button class="btn-action delete-btn" title="Eliminar" onclick="deleteReport('${r.name}')">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>
            </td>
        `;
        listContainer.appendChild(row);
    });
    
    lucide.createIcons();
}

function filtrarReportes() {
    const query = document.getElementById("search-input").value.toLowerCase();
    const filtrados = reportesList.filter(r => r.name.toLowerCase().includes(query));
    renderTableRows(filtrados);
}

// --- GENERAR UN NUEVO REPORTE TÉCNICO ---
async function generarReporteTecnico(event) {
    event.preventDefault();
    
    const btn = document.getElementById("btn-generate");
    const viewerContainer = document.getElementById("viewer-container");
    const actionsHeader = document.getElementById("pdf-actions");
    
    // Obtener campos de texto
    const titulo = document.getElementById("titulo").value;
    const subtitulo = document.getElementById("subtitulo").value;
    const autor = document.getElementById("autor").value;
    const descripcion = document.getElementById("descripcion").value;
    
    // Activar estado de carga (Spinner)
    btn.disabled = true;
    btn.innerHTML = `
        <div class="spinner" style="margin: 0; width: 18px; height: 18px; border-width: 2px;"></div>
        <span>Generando Reporte Local...</span>
    `;
    
    viewerContainer.innerHTML = `
        <div class="viewer-placeholder">
            <div class="spinner" style="width: 32px; height: 32px; border-width: 3px; margin-bottom: 16px;"></div>
            <p>Generando reporte y procesando plano CAD local. Por favor espera...</p>
        </div>
    `;
    
    // Crear objeto FormData para subida de múltiples archivos y texto
    const formData = new FormData();
    formData.append("titulo", titulo);
    formData.append("subtitulo", subtitulo);
    formData.append("autor", autor);
    formData.append("descripcion", descripcion);
    
    // Plano CAD
    if (selectedCadFile) {
        formData.append("cad_file", selectedCadFile);
    }
    
    // Múltiples Imágenes
    selectedImages.forEach(file => {
        formData.append("imagenes", file);
    });
    
    try {
        const response = await fetch("/api/generar-pdf-tecnico/", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Error en el servidor al generar el PDF.");
        }
        
        const data = await response.json();
        
        // PDF Generado Exitosamente
        const relativePdfUrl = `/static/archivos_salida/${data.filename}`;
        
        // Actualizar Visor
        viewerContainer.innerHTML = `
            <iframe class="pdf-iframe" src="${relativePdfUrl}"></iframe>
        `;
        
        // Habilitar botón de descarga
        const btnDownload = document.getElementById("btn-download-pdf");
        btnDownload.href = relativePdfUrl;
        btnDownload.download = data.filename;
        actionsHeader.classList.remove("hidden");
        
        // Limpiar formulario y estados locales
        document.getElementById("pdf-generator-form").reset();
        clearCadFile();
        selectedImages = [];
        document.getElementById("images-preview-grid").innerHTML = "";
        
        // Alerta de éxito suave
        console.log("PDF generado en local: " + data.filename);
        
    } catch (e) {
        viewerContainer.innerHTML = `
            <div class="viewer-placeholder" style="color: var(--accent-red)">
                <i data-lucide="alert-circle" style="color: var(--accent-red)"></i>
                <p><strong>Error de Generación:</strong> ${e.message}</p>
            </div>
        `;
        lucide.createIcons();
    } finally {
        // Restaurar botón
        btn.disabled = false;
        btn.innerHTML = `
            <i data-lucide="file-check"></i>
            <span>Generar Reporte PDF</span>
        `;
        lucide.createIcons();
    }
}

// --- ELIMINAR REPORTE ---
async function deleteReport(filename) {
    if (!confirm(`¿Estás seguro de que deseas eliminar permanentemente el archivo ${filename}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/reportes/${filename}`, {
            method: "DELETE"
        });
        
        if (!response.ok) throw new Error("No se pudo eliminar el reporte.");
        
        // Recargar tabla
        cargarHistorialReportes();
    } catch (e) {
        alert("Error eliminando el archivo: " + e.message);
    }
}

// --- PREVISUALIZACIÓN DE HISTORIAL EN MODAL ---
function previewReport(filename) {
    const modal = document.getElementById("pdf-preview-modal");
    const iframe = document.getElementById("modal-iframe");
    const modalTitle = document.getElementById("modal-title");
    
    modalTitle.textContent = `Previsualización: ${filename}`;
    iframe.src = `/static/archivos_salida/${filename}`;
    modal.classList.remove("hidden");
}

function closeModal() {
    const modal = document.getElementById("pdf-preview-modal");
    const iframe = document.getElementById("modal-iframe");
    
    iframe.src = "";
    modal.classList.add("hidden");
}

// --- GUÍA COLAPSABLE ---
function toggleGuide() {
    const body = document.getElementById("guide-body");
    const chevron = document.getElementById("guide-chevron");
    
    body.classList.toggle("hidden");
    chevron.classList.toggle("rotate");
}

// --- FUNCIONES UTILITARIAS ---
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
