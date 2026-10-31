require 'json'
require 'net/http'
require 'tmpdir'
require 'fileutils'
require 'securerandom'

module SSSurfaceStudio
  extend self
  CHANNELS = {'Normal' => :normal, 'Roughness' => :roughness, 'Metalness' => :metallic, 'AO' => :ao}.freeze

  def data_dir
    exe = Sketchup.read_default('Surface Studio', 'executable', '')
    unless File.file?(exe)
      exe = UI.openpanel('选择 Surface Studio.exe', nil, 'Surface Studio.exe')
      return unless exe
      Sketchup.write_default('Surface Studio', 'executable', exe)
    end
    File.join(File.dirname(exe), 'data')
  end

  def apply_asset(dir, id)
    index = JSON.parse(File.read(File.join(dir, 'index.json'), encoding: 'UTF-8'))
    asset = index.fetch('assets').find { |a| a['id'] == id }
    raise '素材已变更，请重新选择。' unless asset
    raise '请选择 PBR 材质或纯法线素材。' if %w[blend decal].include?(asset['kind'])
    model = Sketchup.active_model
    targets = model.selection.select { |e| e.is_a?(Sketchup::Face) || e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance) }
    raise '请先在模型中选择面、组或组件。' if targets.empty?
    folder = File.join(asset['sourceRoot'] || index.fetch('root'), asset.fetch('folder'))
    assign_maps(model, targets, asset, folder)
  end

  def assign_maps(model, targets, asset, folder)
    maps = {}
    asset.fetch('maps').each do |map|
      channel = map.fetch('channel')
      next unless channel == 'Albedo' || CHANNELS.key?(channel)
      maps[channel] ||= File.join(folder, map.fetch('name'))
    end
    raise '素材没有可用的 PBR 贴图。' if maps.empty?
    model.start_operation('SS 赋予材质', true)
    begin
      mat = model.materials.add(asset.fetch('name'))
      mat.texture = maps['Albedo'] if maps['Albedo']
      CHANNELS.each do |channel, key|
        next unless maps[channel]
        mat.public_send("#{key}_texture=", maps.fetch(channel))
        mat.public_send("#{key}_enabled=", true) if mat.respond_to?("#{key}_enabled=")
      end
      targets.each { |entity| entity.material = mat }
      model.commit_operation
    rescue StandardError
      model.abort_operation
      raise
    end
  end

  def export_material
    model = Sketchup.active_model
    mat = model.selection.filter_map { |e| e.material if e.respond_to?(:material) }.first || model.materials.current
    raise '请先选择有材质的面或对象。' unless mat
    dir = data_dir
    return unless dir
    root = JSON.parse(File.read(File.join(dir, 'config.json'), encoding: 'UTF-8')).fetch('root')
    raise '请先设置 SS 材质库。' unless File.directory?(root)
    textures = {'Albedo' => mat.texture}
    CHANNELS.each do |channel, key|
      textures[channel] = mat.public_send("#{key}_texture") if mat.public_send("#{key}_enabled?")
    end
    raise '所选材质没有可导出的贴图。' if textures.values.compact.empty?
    staging = Dir.mktmpdir('.ss-su-', root)
    begin
      textures.compact.each do |channel, texture|
        path = File.join(staging, "#{channel}.png")
        raise "导出 #{channel} 失败" unless texture.write(path) && File.size?(path)
      end
      File.write(File.join(staging, 'material.json'), JSON.generate(name: mat.display_name))
      label = mat.display_name.gsub(/[[:cntrl:]<>:"\/\\|?*]/, '_')[0,60]
      File.rename(staging, File.join(root, "SU_#{label}_#{SecureRandom.hex(4)}"))
      UI.messagebox('材质已添加到 SS，在材质库中重新扫描即可查看。')
    ensure
      FileUtils.remove_entry(staging) if File.directory?(staging)
    end
  rescue StandardError => e
    UI.messagebox(e.message)
  end

  def open_library
    return @dialog.bring_to_front if @dialog && @dialog.visible?
    dir = data_dir
    return unless dir
    record = JSON.parse(File.read(File.join(dir, 'service.json')))
    port = Integer(record.fetch('port'))
    http = Net::HTTP.new('127.0.0.1', port, nil)
    http.open_timeout = http.read_timeout = 2
    health = JSON.parse(http.get('/api/health').body)
    raise 'SS 服务身份校验失败。' unless health['app'] == 'Surface Studio' && health.fetch('instance') == record.fetch('instance')
    @dialog = UI::HtmlDialog.new(dialog_title: 'Surface Studio · SketchUp', width: 1160, height: 760, resizable: true)
    @dialog.add_action_callback('ss_apply') do |_ctx, id|
      begin
        apply_asset(dir, id)
        Sketchup.status_text = 'SS 材质已赋予，可按 Ctrl+Z 撤销'
      rescue StandardError => e
        UI.messagebox(e.message)
      end
    end
    @dialog.set_url("http://127.0.0.1:#{port}/")
    script = File.read(File.join(__dir__, 'dialog.js'), encoding: 'UTF-8')
    timer = UI.start_timer(0.5, true) { @dialog.execute_script(script) if @dialog && @dialog.visible? }
    @dialog.set_on_closed { UI.stop_timer(timer); @dialog = nil }
    @dialog.show
  rescue StandardError => e
    UI.messagebox("请先启动 SS，再打开材质库。\n#{e.message}")
  end

  def receive_drop(file)
    request = JSON.parse(File.read(file))
    path = request.fetch('path')
    drop = JSON.parse(File.read(path, encoding: 'UTF-8'))
    id = File.basename(file, '.json')
    return unless id.match?(/\A[a-f0-9]{32}\z/) && drop['id'] == id && drop['app'] == 'SurfaceStudio'
    result_file = File.join(File.dirname(File.dirname(path)), 'results', id + '.json')
    begin
      raise '拖放已过期' if drop.fetch('expires') < Time.now.to_f
      asset = drop.fetch('material')
      raise 'SketchUp 暂支持 PBR 材质和法线' if %w[blend decal].include?(asset['kind'])
      model = Sketchup.active_model
      view = model.active_view
      x, y, width, height = request.fetch('point')
      raise '请拖到模型视口内' unless width.positive? && height.positive? && (width.to_f / height - view.vpwidth.to_f / view.vpheight).abs < 0.015
      pick = view.pick_helper
      pick.do_pick(x.to_f * view.vpwidth / width, y.to_f * view.vpheight / height)
      entity = pick.best_picked
      raise '落点没有可赋材质的对象' unless [Sketchup::Face, Sketchup::Group, Sketchup::ComponentInstance].any? { |type| entity.is_a?(type) }
      assign_maps(model, [entity], asset, File.join(asset.fetch('root'),asset.fetch('folder')))
      status, message = 'success', '已赋予到 SketchUp，可按 Ctrl+Z 撤销'
    rescue StandardError => e
      status, message = 'error', e.message
    end
    tmp = result_file + '.su-tmp'
    File.write(tmp, JSON.generate(id: id, status: status, message: message, expires: drop['expires']))
    File.rename(tmp, result_file)
  ensure
    File.delete(file) if File.exist?(file)
  end

  def listen_for_drops
    inbox = File.join(ENV.fetch('LOCALAPPDATA'), 'SurfaceStudio', 'sketchup', Process.pid.to_s)
    FileUtils.mkdir_p(inbox)
    ready = File.join(inbox, 'ready')
    FileUtils.touch(ready)
    UI.start_timer(0.2, true) do
      begin
        FileUtils.touch(ready) if Time.now - File.mtime(ready) > 4
        # Windows environment paths contain backslashes, which glob treats as escapes.
        name = Dir.children(inbox).find { |entry| entry.match?(/\A[a-f0-9]{32}\.json\z/) }
        receive_drop(File.join(inbox, name)) if name
      rescue StandardError => e
        warn "Surface Studio: #{e.message}"
      end
    end
  end

  unless file_loaded?(__FILE__)
    listen_for_drops
    UI.menu('Extensions').add_item('Surface Studio · 打开材质库') { open_library }
    UI.menu('Extensions').add_item('Surface Studio · 添加材质到 SS') { export_material }
    file_loaded(__FILE__)
  end
end


