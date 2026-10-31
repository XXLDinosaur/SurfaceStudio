require 'sketchup.rb'
require 'extensions.rb'
module SSSurfaceStudio
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Surface Studio 材质库', 'ss_surface_studio/bridge')
    extension.version = '0.2.0'
    extension.description = '浏览 Surface Studio 本地素材并赋予 SketchUp 对象。'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
