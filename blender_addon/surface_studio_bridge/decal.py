"""Independent, undoable surface decals. Target mesh/materials remain untouched."""
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from bpy_extras import view3d_utils

KEYMAPS=[]

class SurfaceSlide:
    """A fixed evaluated target and a transported frame, independent of G depth."""
    def __init__(self,target,graph,world):
        evaluated=target.evaluated_get(graph);mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles();matrix=evaluated.matrix_world
            self.vertices=[matrix@v.co for v in mesh.vertices]
            normal_matrix=matrix.to_3x3().inverted().transposed()
            self.normals=[(normal_matrix@v.normal).normalized() for v in mesh.vertices]
            self.triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
            self.tree=BVHTree.FromPolygons(self.vertices,self.triangles,all_triangles=True)
            # Lock this gesture to the connected surface patch. Vertex normals
            # may be smooth even across a cube edge; use geometry for barriers.
            normals=[(self.vertices[b]-self.vertices[a]).cross(self.vertices[c]-self.vertices[a]).normalized()
                     for a,b,c in self.triangles]
            edges={}
            neighbors=[set() for _ in self.triangles]
            for i,triangle in enumerate(self.triangles):
                for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                    edge=tuple(sorted((a,b)))
                    for other in edges.get(edge,[]):
                        if normals[i].dot(normals[other])>.70710678:
                            neighbors[i].add(other);neighbors[other].add(i)
                    edges.setdefault(edge,[]).append(i)
            _,_,seed,_=self.tree.find_nearest(world.translation)
            self.patch=set();pending=[] if seed is None else [seed]
            while pending:
                current=pending.pop()
                if current in self.patch:continue
                self.patch.add(current)
                pending.extend(neighbors[current]-self.patch)
            # Interpolate only within the patch: smooth curved motion without
            # borrowing normals from the other side of a hard corner.
            self.normals=[Vector((0,0,0)) for _ in self.vertices]
            for i in self.patch:
                for vertex in self.triangles[i]:self.normals[vertex]+=normals[i]
            self.normals=[n.normalized() for n in self.normals]
        finally:evaluated.to_mesh_clear()
        self.world=world.copy()

    def move(self,origin,direction):
        point,normal,index,_=self.tree.ray_cast(origin,direction.normalized())
        if point is None or index not in self.patch:return None
        ids=self.triangles[index]
        smooth=barycentric_transform(point,*(self.vertices[i] for i in ids),*(self.normals[i] for i in ids))
        if smooth.length>.001 and smooth.dot(normal)>0:normal=smooth.normalized()
        old_normal=(self.world.to_3x3()@Vector((0,0,1))).normalized()
        # Carry the previous tangent frame across the surface instead of choosing
        # a new global up axis at every hit (which flips near a pole).
        rotation=old_normal.rotation_difference(normal)@self.world.to_quaternion()
        self.world=Matrix.LocRotScale(point,rotation,self.world.to_scale())
        return self.world.copy()

class SURFACESTUDIO_OT_slide_decal(bpy.types.Operator):
    bl_idname='surface_studio.slide_decal';bl_label='沿表面移动贴花';bl_options={'REGISTER','UNDO','BLOCKING'}
    @classmethod
    def poll(cls,context):
        return bool(context.mode=='OBJECT' and context.object and context.object.get('ss_decal')
                    and context.area and context.area.type=='VIEW_3D' and context.region)
    def invoke(self,context,event):
        obj=context.object
        wrap=next((m for m in obj.modifiers if m.type=='SHRINKWRAP' and m.target),None)
        if not wrap:
            self.report({'WARNING'},'找不到贴花目标模型');return {'CANCELLED'}
        self.obj=obj;self.before=obj.matrix_basis.copy()
        self.constraint=obj.constraints.get('SS Surface Attachment')
        self.was_muted=self.constraint.mute if self.constraint else False
        graph=context.evaluated_depsgraph_get()
        world=obj.evaluated_get(graph).matrix_world.copy()
        try:self.slide=SurfaceSlide(wrap.target,graph,world)
        except Exception as error:
            self.report({'ERROR'},str(error));return {'CANCELLED'}
        if self.constraint:self.constraint.mute=True
        obj.matrix_world=world
        self.region=next((r for r in getattr(context.area,'regions',[]) if r.type=='WINDOW'),context.region)
        self.view=getattr(getattr(context,'space_data',None),'region_3d',None)
        self.mouse_offset=Vector((0,0))
        if self.view and event:
            centre=view3d_utils.location_3d_to_region_2d(self.region,self.view,world.translation)
            if centre is not None:
                self.mouse_offset=centre-Vector((event.mouse_x-self.region.x,event.mouse_y-self.region.y))
        self.changed=False
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set('移动鼠标沿模型表面滑动 · 左键/Enter 确认 · 右键/Esc 取消')
        return {'RUNNING_MODAL'}
    def restore(self):
        self.obj.matrix_basis=self.before
        if self.constraint:self.constraint.mute=self.was_muted
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            self.restore();context.area.header_text_set(None);return {'CANCELLED'}
        if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'} and event.value=='PRESS':
            if not self.changed:self.restore()
            context.area.header_text_set(None);return {'FINISHED'}
        if event.type=='MOUSEMOVE':
            region=self.region;view=self.view
            coord=Vector((event.mouse_x-region.x,event.mouse_y-region.y))+self.mouse_offset
            origin=view3d_utils.region_2d_to_origin_3d(region,view,coord)
            direction=view3d_utils.region_2d_to_vector_3d(region,view,coord)
            world=self.slide.move(origin,direction)
            if world is not None:self.obj.matrix_world=world;self.changed=True
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

def register_slide_keymap():
    config=bpy.context.window_manager.keyconfigs.addon
    if config:
        keymap=config.keymaps.new(name='3D View',space_type='VIEW_3D')
        item=keymap.keymap_items.new('surface_studio.slide_decal','G','PRESS',head=True)
        KEYMAPS.append((keymap,item))

def unregister_slide_keymap():
    for keymap,item in KEYMAPS:keymap.keymap_items.remove(item)
    KEYMAPS.clear()

def attach_surface(obj,target):
    """Anchor the decal centre and frame before deforming its mesh to the surface."""
    constraint=obj.constraints.get('SS Surface Attachment')
    if constraint is None:constraint=obj.constraints.new('SHRINKWRAP')
    constraint.name='SS Surface Attachment';constraint.target=target
    constraint.shrinkwrap_type='NEAREST_SURFACE'
    constraint.use_track_normal=True;constraint.track_axis='TRACK_Z'

def improve_surface(obj):
    """Subdivide before projection so face interiors don't bridge through curves."""
    wrap=next((m for m in obj.modifiers if m.type=='SHRINKWRAP'),None)
    if wrap is None:return
    detail=obj.modifiers.get('SS Surface Detail')
    if detail is None:detail=obj.modifiers.new('SS Surface Detail','SUBSURF')
    detail.subdivision_type='SIMPLE';detail.levels=2;detail.render_levels=2
    detail_index=list(obj.modifiers).index(detail);wrap_index=list(obj.modifiers).index(wrap)
    if detail_index>wrap_index:obj.modifiers.move(detail_index,wrap_index)
    extent=max(max(v.co.x for v in obj.data.vertices)-min(v.co.x for v in obj.data.vertices),
               max(v.co.y for v in obj.data.vertices)-min(v.co.y for v in obj.data.vertices))
    wrap.offset=max(wrap.offset,extent*.002,.00005)
    obj['ss_surface_revision']=2

def place(context,target,location,normal,manifest,build_material,options):
    if target.get('ss_decal'):raise ValueError('请把新贴花拖到原模型上，而不是另一张贴花')
    if not any(m['channel']=='Opacity' for m in manifest['maps']):raise ValueError('贴花缺少 Opacity 遮罩')
    normal=Vector(normal)
    if normal.length<.001:raise ValueError('无法确定贴花表面方向')
    material,_=build_material(manifest,{**options,'repeat':1,'bump':False})
    # Each decal has independent opacity controls.
    material=material.copy();material.name='SS 贴花 · '+manifest['name']
    nodes=material.node_tree.nodes;links=material.node_tree.links
    shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    mask=nodes.get('Opacity');strength=nodes.new('ShaderNodeMath');strength.name='SS Decal Opacity';strength.label='贴花透明度';strength.operation='MULTIPLY';strength.inputs[1].default_value=1
    strength.use_clamp=True
    links.new(mask.outputs['Color'],strength.inputs[0]);links.new(strength.outputs[0],shader.inputs['Alpha'])
    for n in nodes:
        if n.type=='TEX_IMAGE':n.extension='CLIP'
    color=nodes.get('Albedo');ratio=color.image.size[1]/max(1,color.image.size[0]) if color else 1
    width=max(.01,max(target.dimensions)*.25);height=width*ratio
    mesh=bpy.data.meshes.new('SS 贴花网格');obj=None
    try:
        count=24
        # Start slightly above the hit plane: rays starting exactly on the
        # surface can miss it through floating-point error and cause z-fighting.
        vertices=[((x/count-.5)*width,(y/count-.5)*height,width*.01) for y in range(count+1) for x in range(count+1)]
        faces=[(y*(count+1)+x,y*(count+1)+x+1,(y+1)*(count+1)+x+1,(y+1)*(count+1)+x) for y in range(count) for x in range(count)]
        mesh.from_pydata(vertices,[],faces);mesh.update();uv=mesh.uv_layers.new()
        for face in mesh.polygons:
            for li in face.loop_indices:
                v=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=(v.x/width+.5,v.y/height+.5)
        obj=bpy.data.objects.new('贴花 · '+manifest['name'],mesh);context.collection.objects.link(obj)
        obj.location=location;obj.rotation_euler=normal.normalized().to_track_quat('Z','Y').to_euler()
        mesh.materials.append(material)
        mod=obj.modifiers.new('贴合表面','SHRINKWRAP');mod.target=target;mod.wrap_method='PROJECT';mod.use_project_z=True;mod.use_negative_direction=True;mod.use_positive_direction=True;mod.project_limit=max(width,height)*.5;mod.offset=max(.00005,width*.001)
        context.view_layer.update();world=obj.matrix_world.copy()
        obj.parent=target;obj.matrix_parent_inverse=target.matrix_world.inverted();obj.matrix_world=world
        attach_surface(obj,target)
        improve_surface(obj)
        obj['ss_decal']=True;obj['ss_decal_target']=target.name
        if hasattr(obj,'visible_shadow'):obj.visible_shadow=False
        for item in context.selected_objects:item.select_set(False)
        obj.select_set(True);context.view_layer.objects.active=obj
        return {'status':'success','material':material.name,'objects':[obj.name],'faces':len(faces),'autoUV':0,'warnings':[],'message':'已添加独立贴花，可在 N 侧栏调整；Ctrl+Z 撤销'}
    except Exception:
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        if material.users==0:bpy.data.materials.remove(material)
        raise

class SURFACESTUDIO_OT_attach_decal(bpy.types.Operator):
    bl_idname='surface_studio.attach_decal';bl_label='修复贴合 / 启用移动贴合';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.object and context.object.get('ss_decal'))
    def execute(self,context):
        obj=context.object
        mod=next((m for m in obj.modifiers if m.type=='SHRINKWRAP' and m.target),None)
        if not mod:
            self.report({'WARNING'},'找不到贴花目标模型');return {'CANCELLED'}
        attach_surface(obj,mod.target)
        improve_surface(obj)
        return {'FINISHED'}

class SURFACESTUDIO_PT_decal(bpy.types.Panel):
    bl_label='贴花调整';bl_idname='SURFACESTUDIO_PT_decal';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Surface Studio'
    @classmethod
    def poll(cls,context):return bool(context.object and context.object.get('ss_decal'))
    def draw(self,context):
        obj=context.object;layout=self.layout
        layout.label(text='独立贴花 · 原模型材质保持不变')
        layout.operator('surface_studio.slide_decal')
        layout.prop(obj,'scale',text='尺寸')
        layout.prop(obj,'delta_rotation_euler',index=2,text='旋转')
        if obj.active_material:
            node=obj.active_material.node_tree.nodes.get('SS Decal Opacity')
            if node:layout.prop(node.inputs[1],'default_value',text='不透明度',slider=True)
        mod=next((m for m in obj.modifiers if m.type=='SHRINKWRAP'),None)
        if mod:layout.prop(mod,'offset',text='表面偏移')
        if not obj.constraints.get('SS Surface Attachment') or obj.get('ss_surface_revision',0)<2:
            layout.operator('surface_studio.attach_decal')
        layout.label(text='G 沿表面移动 · S 缩放 · X 删除')
