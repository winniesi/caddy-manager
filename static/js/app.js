/**
 * Caddy Manager - Frontend Application
 */

// 全局状态
let domains = [];
let deleteIndex = -1;

// DOM 元素
const elements = {
    domainTable: document.getElementById('domainTable'),
    emptyState: document.getElementById('emptyState'),
    domainCount: document.getElementById('domainCount'),
    subdomain: document.getElementById('subdomain'),
    port: document.getElementById('port'),
    btnAdd: document.getElementById('btnAdd'),
    btnSave: document.getElementById('btnSave'),
    btnScanPorts: document.getElementById('btnScanPorts'),
    btnSyncDdns: document.getElementById('btnSyncDdns'),
    btnViewLog: document.getElementById('btnViewLog'),
    portModal: document.getElementById('portModal'),
    portList: document.getElementById('portList'),
    portSearch: document.getElementById('portSearch'),
    btnCloseModal: document.getElementById('btnCloseModal'),
    logModal: document.getElementById('logModal'),
    logContent: document.getElementById('logContent'),
    btnCloseLogModal: document.getElementById('btnCloseLogModal'),
    deleteModal: document.getElementById('deleteModal'),
    deleteDomain: document.getElementById('deleteDomain'),
    btnCancelDelete: document.getElementById('btnCancelDelete'),
    btnConfirmDelete: document.getElementById('btnConfirmDelete'),
    btnCloseDeleteModal: document.getElementById('btnCloseDeleteModal'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    lastSync: document.getElementById('lastSync'),
    syncDomains: document.getElementById('syncDomains'),
    toast: document.getElementById('toast'),
    toastIcon: document.getElementById('toastIcon'),
    toastMessage: document.getElementById('toastMessage'),
};

// API 调用
async function api(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    const response = await fetch(`/api${endpoint}`, options);
    return response.json();
}

// 显示提示消息
function showToast(message, type = 'success') {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
    };
    elements.toastIcon.textContent = icons[type] || icons.info;
    elements.toastMessage.textContent = message;
    elements.toast.className = 'toast show';

    setTimeout(() => {
        elements.toast.className = 'toast';
    }, 3000);
}

// 渲染域名表格
function renderDomains() {
    const tbody = elements.domainTable;
    tbody.innerHTML = '';

    if (domains.length === 0) {
        elements.emptyState.classList.add('show');
        elements.domainCount.textContent = '0 个域名';
        return;
    }

    elements.emptyState.classList.remove('show');
    elements.domainCount.textContent = `${domains.length} 个域名`;

    domains.forEach((domain, index) => {
        const tr = document.createElement('tr');
        const link = `https://${domain.domain}:8443`;
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>
                <a href="${link}" target="_blank" class="domain-link" title="打开 ${link}">
                    ${domain.subdomain}
                </a>
                <span class="domain-suffix">.winnie.si</span>
            </td>
            <td>
                <code class="port-code">${domain.port}</code>
            </td>
            <td>
                <button class="btn btn-icon btn-delete" data-index="${index}" title="删除">
                    🗑️
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // 绑定删除按钮事件
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.currentTarget.dataset.index);
            showDeleteConfirm(index);
        });
    });
}

// 加载配置
async function loadConfig() {
    try {
        const result = await api('/config');
        if (result.success) {
            domains = result.domains || [];
            renderDomains();
        }
    } catch (error) {
        showToast('加载配置失败', 'error');
    }
}

// 保存配置
async function saveConfig() {
    const btn = elements.btnSave;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 保存中...';

    try {
        const result = await api('/restart_and_sync', 'POST', { domains });
        if (result.success) {
            showToast('配置已保存，Caddy 已重启，DDNS 已同步', 'success');
            updateDdnsStatus();
        } else {
            showToast('保存失败: ' + (result.error || ''), 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">💾</span> 保存配置';
    }
}

// 添加域名
function addDomain() {
    const subdomain = elements.subdomain.value.trim();
    const port = parseInt(elements.port.value);

    if (!subdomain) {
        showToast('请输入子域名', 'warning');
        return;
    }

    if (!port || port < 1 || port > 65535) {
        showToast('请输入有效端口 (1-65535)', 'warning');
        return;
    }

    // 检查子域名是否已存在
    if (domains.some(d => d.subdomain === subdomain)) {
        showToast('子域名已存在', 'warning');
        return;
    }

    // 生成 name（下划线替换连字符）
    const name = subdomain.replace(/-/g, '_');

    domains.push({
        name,
        domain: `${subdomain}.winnie.si`,
        subdomain,
        port,
    });

    renderDomains();
    elements.subdomain.value = '';
    elements.port.value = '';
    showToast(`已添加 ${subdomain}.winnie.si`, 'success');
}

// 显示删除确认
function showDeleteConfirm(index) {
    deleteIndex = index;
    elements.deleteDomain.textContent = domains[index].domain;
    elements.deleteModal.classList.add('show');
}

// 确认删除
function confirmDelete() {
    if (deleteIndex >= 0 && deleteIndex < domains.length) {
        const domain = domains[deleteIndex];
        domains.splice(deleteIndex, 1);
        renderDomains();
        showToast(`已删除 ${domain.domain}`, 'success');
    }
    closeDeleteModal();
}

// 关闭删除弹窗
function closeDeleteModal() {
    elements.deleteModal.classList.remove('show');
    deleteIndex = -1;
}

// 扫描端口
async function scanPorts() {
    const btn = elements.btnScanPorts;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span>';

    try {
        const result = await api('/scan_ports');
        if (result.success) {
            renderPortList(result.ports);
            elements.portModal.classList.add('show');
        } else {
            showToast('扫描端口失败', 'error');
        }
    } catch (error) {
        showToast('扫描端口失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '扫描端口';
    }
}

// 渲染端口列表
function renderPortList(ports) {
    elements.portList.innerHTML = '';

    if (ports.length === 0) {
        elements.portList.innerHTML = '<div class="empty-state show"><p>未发现监听端口</p></div>';
        return;
    }

    // 获取已使用的端口
    const usedPorts = new Set(domains.map(d => d.port));

    ports.forEach(port => {
        const isUsed = usedPorts.has(port.port);
        const div = document.createElement('div');
        div.className = `port-item ${isUsed ? 'port-used' : ''}`;
        div.innerHTML = `
            <span class="port-number">${port.port}</span>
            <span class="port-service">${port.service}</span>
            <span class="port-container">${port.container}</span>
            ${isUsed ? '<span class="port-badge">已添加</span>' : ''}
        `;
        if (!isUsed) {
            div.addEventListener('click', () => {
                elements.port.value = port.port;
                closePortModal();
            });
        }
        elements.portList.appendChild(div);
    });
}

// 关闭端口模态框
function closePortModal() {
    elements.portModal.classList.remove('show');
    elements.portSearch.value = '';
}

// 搜索端口
function searchPorts() {
    const query = elements.portSearch.value.toLowerCase();
    const items = elements.portList.querySelectorAll('.port-item');

    items.forEach(item => {
        const port = item.querySelector('.port-number').textContent;
        const service = item.querySelector('.port-service').textContent.toLowerCase();
        const container = item.querySelector('.port-container').textContent.toLowerCase();

        const match = port.includes(query) || service.includes(query) || container.includes(query);
        item.style.display = match ? 'flex' : 'none';
    });
}

// 同步 DDNS
async function syncDdns() {
    const btn = elements.btnSyncDdns;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 同步中...';

    try {
        const result = await api('/sync_ddns', 'POST');
        if (result.success) {
            showToast('DDNS 同步完成', 'success');
            updateDdnsStatus();
        } else {
            showToast('DDNS 同步失败: ' + (result.output || result.error || ''), 'error');
        }
    } catch (error) {
        showToast('DDNS 同步失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🔄</span> 立即同步';
    }
}

// 查看日志
async function viewLog() {
    elements.logModal.classList.add('show');
    elements.logContent.textContent = '加载中...';

    try {
        const result = await api('/ddns_log?lines=100');
        if (result.success) {
            elements.logContent.textContent = result.log;
            // 滚动到底部
            elements.logContent.scrollTop = elements.logContent.scrollHeight;
        } else {
            elements.logContent.textContent = '加载日志失败';
        }
    } catch (error) {
        elements.logContent.textContent = '加载日志失败: ' + error.message;
    }
}

// 关闭日志模态框
function closeLogModal() {
    elements.logModal.classList.remove('show');
}

// 更新 DDNS 状态
async function updateDdnsStatus() {
    try {
        const result = await api('/ddns_log?lines=20');
        if (result.success) {
            const log = result.log;
            const lines = log.split('\n').reverse();

            // 解析最后同步时间
            let lastSyncTime = '-';
            let syncDomainsCount = '-';
            let status = 'unknown';

            for (const line of lines) {
                if (line.includes('脚本运行完成')) {
                    const match = line.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
                    if (match) {
                        lastSyncTime = match[1];
                    }
                    status = 'success';
                    break;
                }
                if (line.includes('同步完成')) {
                    status = 'success';
                }
                if (line.includes('发现需要管理的子域名')) {
                    const count = (log.match(/发现需要管理的子域名/g) || []).length;
                    syncDomainsCount = `${count} 个`;
                }
            }

            // 更新 UI
            elements.lastSync.textContent = lastSyncTime;
            elements.syncDomains.textContent = syncDomainsCount;

            // 更新状态指示器
            elements.statusDot.className = 'status-dot';
            if (status === 'success') {
                elements.statusDot.classList.add('success');
                elements.statusText.textContent = '同步完成';
            } else if (status === 'error') {
                elements.statusDot.classList.add('error');
                elements.statusText.textContent = '同步失败';
            } else {
                elements.statusText.textContent = '未知';
            }
        }
    } catch (error) {
        console.error('更新 DDNS 状态失败:', error);
    }
}

// 事件绑定
function bindEvents() {
    // 添加域名
    elements.btnAdd.addEventListener('click', addDomain);
    elements.subdomain.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addDomain();
    });
    elements.port.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addDomain();
    });

    // 保存配置
    elements.btnSave.addEventListener('click', saveConfig);

    // 扫描端口
    elements.btnScanPorts.addEventListener('click', scanPorts);

    // 同步 DDNS
    elements.btnSyncDdns.addEventListener('click', syncDdns);

    // 查看日志
    elements.btnViewLog.addEventListener('click', viewLog);

    // 关闭模态框
    elements.btnCloseModal.addEventListener('click', closePortModal);
    elements.btnCloseLogModal.addEventListener('click', closeLogModal);
    elements.btnCloseDeleteModal.addEventListener('click', closeDeleteModal);
    elements.btnCancelDelete.addEventListener('click', closeDeleteModal);
    elements.btnConfirmDelete.addEventListener('click', confirmDelete);

    // 点击模态框外部关闭
    elements.portModal.addEventListener('click', (e) => {
        if (e.target === elements.portModal) closePortModal();
    });
    elements.logModal.addEventListener('click', (e) => {
        if (e.target === elements.logModal) closeLogModal();
    });
    elements.deleteModal.addEventListener('click', (e) => {
        if (e.target === elements.deleteModal) closeDeleteModal();
    });

    // 搜索端口
    elements.portSearch.addEventListener('input', searchPorts);

    // ESC 键关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePortModal();
            closeLogModal();
            closeDeleteModal();
        }
    });
}

// 初始化
async function init() {
    bindEvents();
    await loadConfig();
    await updateDdnsStatus();
}

// 启动应用
init();
