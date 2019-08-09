bl_info = {
	'name' : 'Actions to Panda3D .egg files batch export',
	'description' : 'Batch export of Blender actions to Panda3D animation .egg files.',
	'author' : 'Viktoria Danchenko',
	'version' : (0, 4),
	'blender' : (2, 80, 0),
	'location' : '3D View > N Panel > Batch .egg animation export',
	'category' : 'Import-Export',
	'wiki_url': 'https://github.com/vika-sonne/batch-egg-file-animation-export',
	'tracker_url': 'https://github.com/vika-sonne/batch-egg-file-animation-export/issues',
}


from os import path
from math import pi
from typing import List, Dict, Optional
import bpy
from bpy.utils import register_class, unregister_class
from mathutils import Matrix, Euler


class View3DPanel:
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'


class EGG_OT_add_animation(bpy.types.Operator):
	'Add current animation to export animations list'
	bl_idname = 'actions_to_egg.add_current_action'
	bl_label = 'Add current action'

	@classmethod
	def poll(cls, context):
		try:
			current_action_name = context.active_object.animation_data.action.name
		except:
			return False
		try:
			return current_action_name not in context.object.actions_to_egg.animations
		except:
			return False
		return True

	def execute(self, context):
		try:
			ob = context.object.actions_to_egg
		except:
			pass
		else:
			i = ob.animations.add()
			i.select = True
			i.name = context.active_object.animation_data.action.name
			i.export_name = i.name
		return {'FINISHED'}


class EGG_OT_remove_animation(bpy.types.Operator):
	'Remove current selected action from actions list'
	bl_idname = 'actions_to_egg.remove_action'
	bl_label = 'Remove action'

	@classmethod
	def poll(cls, context):
		try:
			return len(context.object.actions_to_egg.animations) > 0
		except:
			return False
		return True

	def execute(self, context):
		ob = context.object.actions_to_egg
		ob.animations.remove(ob.animations_index)
		return {'FINISHED'}


class EGG_OT_add_all_actions(bpy.types.Operator):
	bl_idname = 'actions_to_egg.add_all_actions'
	bl_label = 'Add all actions'

	@classmethod
	def poll(cls, context):
		try:
			return len(bpy.data.actions) > 0
		except:
			pass
		return False

	def execute(self, context):
		try:
			ob = context.object.actions_to_egg
		except:
			pass
		else:
			context.window.cursor_set('WAIT')

			for act in bpy.data.actions:
				if act.name in ob.animations:
					continue # action already in export animation list # skip adding
				i = ob.animations.add()
				i.select = True
				i.name = act.name
				i.export_name = i.name

			context.window.cursor_set('DEFAULT')

		return {'FINISHED'}


class EGG_OT_clear_animations_list(bpy.types.Operator):
	bl_idname = 'actions_to_egg.clear_animations_list'
	bl_label = 'Clear export animations list'

	@classmethod
	def poll(cls, context):
		try:
			return len(context.object.actions_to_egg.animations) > 0
		except:
			pass
		return False

	def execute(self, context):
		try:
			ob = context.object.actions_to_egg
		except:
			pass
		else:
			ob.animations.clear()
		return {'FINISHED'}


class EGG_OT_deselect_all_animations(bpy.types.Operator):
	bl_idname = 'actions_to_egg.deselect_all_animations'
	bl_label = 'Deselect all export animations'

	@classmethod
	def poll(cls, context):
		try:
			if len(context.object.actions_to_egg.animations) > 0:
				for animation_item in context.object.actions_to_egg.animations:
					if animation_item.select:
						return True
		except:
			pass
		return False

	def execute(self, context):
		try:
			ob = context.object.actions_to_egg
		except:
			pass
		else:
			for animation_item in ob.animations:
				animation_item.select = False
		return {'FINISHED'}


class EGG_OT_invert_select_animations(bpy.types.Operator):
	bl_idname = 'actions_to_egg.invert_select_animations'
	bl_label = 'Invert export animations selection'

	@classmethod
	def poll(cls, context):
		try:
			return len(context.object.actions_to_egg.animations) > 0
		except:
			pass
		return False

	def execute(self, context):
		try:
			ob = context.object.actions_to_egg
		except:
			pass
		else:
			for animation_item in ob.animations:
				animation_item.select = not animation_item.select
		return {'FINISHED'}


def show_animations_popup_menu(self, context):
	layout = self.layout
	layout.operator('actions_to_egg.deselect_all_animations')
	layout.operator('actions_to_egg.invert_select_animations')
	layout.separator()
	layout.operator('actions_to_egg.add_all_actions')
	layout.operator('actions_to_egg.clear_animations_list', icon='X')


class EGG_OT_animations_popup_menu(bpy.types.Operator):
	bl_idname = 'actions_to_egg.animations_popup_menu'
	bl_label = ''

	@classmethod
	def poll(cls, context):
		try:
			return len(context.object.actions_to_egg.animations) > 0 or len(bpy.data.actions) > 0
		except:
			pass
		return False

	def execute(self, context):
		context.window_manager.popup_menu(show_animations_popup_menu)
		return {'FINISHED'}


class Animation():
	'''Bones animation'''
	__slots__ = 'name', 'frames_from', 'frames_to', 'fps', 'bones'

	def __init__(self):
		self.bones: Dict(str, 'Animation.Bone') = {}

	def get_bone(self, name: str) -> 'Animation.Bone':
		'Gets bone by name; if bone not found - creates & appends it'
		try:
			return self.bones[name]
		except:
			# bone not found # create the bone
			bone = Animation.Bone()
			self.bones[name] = bone
			return bone

	class Bone():
		__slots__ = 'envelopes'

		def __init__(self):
			self.envelopes: Dict[str, 'Animation.Envelope'] = {} # envelope name, envelope

		def add_envelope_value(self, envelope_name: str, value: float):
			try:
				envelope = self.envelopes[envelope_name]
			except:
				self.envelopes[envelope_name] = Animation.Envelope(value)
			else:
				envelope.add_value(value)

	class Envelope():
		'Contains values (one or for all animation frames)'
		__slots__ = 'values', '_filter_count'

		def __init__(self, value: float):
			self.values = [ value, ]
			self._filter_count = 1

		def add_value(self, value: float):
			if len(self.values) > 1:
				self.values.append(value)
			elif abs(self.values[0] - value) < .0001:
				# one value # filter the same value for rest frames
				self._filter_count += 1
			elif self._filter_count > 1:
				# cancel filter the same value
				self.values += [ self.values[0], ] * (self._filter_count)
				self._filter_count = 0
			else:
				# add the second value
				self.values.append(value)


def export_action_to_egg_file(act: bpy.types.Action, ob: Optional[bpy.types.Object] = None,
		file_path: Optional[str] = None):
	'Exports action to .egg animation'

	def _get_bones_structure() -> Dict[bpy.types.Bone, Optional[Dict]]:
		'Returns dict of dicts ... of bones according the armature bones structure'
		def _find_children(parent_bone: bpy.types.Bone) -> Optional[Dict[bpy.types.Bone, Optional[Dict]]]:
			'Returns children bones'
			ret : Dict[bpy.types.Bone, Dict] = {}
			for bone in ob.data.bones:
				if bone.parent == parent_bone:
					ret[bone] = _find_children(bone)
			return ret if ret else None
		# collect children for top-level bones
		ret : Dict[bpy.types.Bone, Dict] = {}
		for bone in ob.data.bones:
			if bone.parent is None:
				ret[bone] = _find_children(bone)
		return ret

	def _print_bones_structure(bones: Dict[bpy.types.Bone, Optional[Dict]], indent: str = ''):
		for i in bones.items():
			print(indent + i[0].name)
			if i[1]:
				_print_bones_structure(i[1], indent + '\t')

	def _dump_bones_animation(parent_bone: bpy.types.Bone, children: Dict[bpy.types.Bone, Optional[Dict]],
			indent: str) -> str:

		def _dump_bone_animation(bone: Animation.Bone, indent: str) -> str:
			'Dumps bones to Xfm$Anim entry'
			# see https://github.com/panda3d/panda3d/blob/master/panda/src/doc/eggSyntax.txt
			# <Xfm$Anim_S$> name {
			# 	<Scalar> fps { 24 }
			# 	<Scalar> order { srpht }
			# 	<S$Anim> i { ... }
			# 	<S$Anim> j { ... }
			# 	...
			# }
			# s       - all scale and shear transforms
			# r, p, h - individual rotate transforms
			# t       - all translation transforms
			# i, j, k - scale in x, y, z directions, respectively
			# a, b, c - shear in xy, xz, and yz planes, respectively
			# r, p, h - rotate by roll, pitch, heading
			# x, y, z - translate in x, y, z directions
			ret = indent + '<Xfm$Anim_S$> xform {\n'
			ret += indent + '\t<Scalar> fps {{{}}}\n'.format(animation.fps)
			ret += indent + '\t<Scalar> order {sprht}\n'
			for i in animation.get_bone(bone.name).envelopes.items():
				ret += indent + '\t<S$Anim> {} {{ <V> {{'.format(i[0])
				if len(i[1].values) > 1:
					ret += ' '.join([ '{:.4f}'.format(ii) for ii in i[1].values ]) + '} }\n'
				else:
					ret += '{:.4f}'.format(i[1].values[0]) + '} }\n'
			ret += indent + '}\n'
			return ret

		buff = indent + '<Table> {} {{\n'.format(parent_bone.name)
		buff += _dump_bone_animation(parent_bone, indent + '\t')
		if children:
			for i in children.items():
				buff += _dump_bones_animation(i[0], i[1], indent + '\t')
		buff += indent + '}\n'
		return buff


	if ob is None:
		ob = bpy.context.active_object
	if not ob.animation_data:
		ob.animation_data_create()
	# _print_bones_structure(_get_bones_structure())
	# return
	ob.animation_data.action = act
	# export animation frames according to the armature bones structure
	# collect bones matrices frame by frame
	animation = Animation()
	animation.frames_from, animation.frames_to = int(act.frame_range[0]), int(act.frame_range[1])
	animation.fps = bpy.context.scene.render.fps
	for f in range(animation.frames_from, animation.frames_to + 1): # blender frame_range contains inclusive values, but range - exclusive
		bpy.context.scene.frame_current = f
		bpy.context.scene.frame_set(f)
		for bone in ob.pose.bones:
			# get or add bone
			animation_bone = animation.get_bone(bone.name)
			# get bone matrix
			if bone.parent:
				matrix = bone.parent.matrix.inverted() @ bone.matrix
			else:
				matrix = ob.matrix_world @ bone.matrix
			# add envelopes from bone matrix
			for envelope_name, value in zip('ijk', matrix.to_scale()):
				animation_bone.add_envelope_value(envelope_name, value)
			for envelope_name, value in zip('prh', matrix.to_euler()):
				animation_bone.add_envelope_value(envelope_name, value / pi * 180)
			for envelope_name, value in zip('xyz', matrix.to_translation()):
				animation_bone.add_envelope_value(envelope_name, value)

	# check frames count consistency
	# frames_count = animation.frames_to - animation.frames_from + 1
	# for bone_name, bone in animation.bones.items():
	# 	for envelope_name, envelope in bone.envelopes.items():
	# 		if len(envelope.values) > 1 and len(envelope.values) != frames_count:
	# 			print('Frames for bone {} envelope {} {} != {}'.format(bone_name, envelope_name, len(envelope.values), frames_count))
	# del frames_count

	# .egg file buffer
	buff = '<Comment> {{"{}" by Blender add-on "Actions to Panda3D .egg files batch export"}}\n'.format(act.name)
	buff += '<CoordinateSystem> {{ Z-up }}\n<Table> {{\n\t<Bundle> {} {{\n'.format(ob.name)
	buff += '\t\t<Table> "<skeleton>" {\n'
	bones_structure = _get_bones_structure()
	# go thru top-level bones
	for i in bones_structure.items():
		buff += _dump_bones_animation(i[0], i[1], '\t\t\t')

	buff += '\t\t}\n\t}\n}\n' # close bundle

	if file_path:
		# write to .egg file
		with open(file_path, 'w') as f:
			f.write(buff)
	else:
		# copy to clipboard
		bpy.context.window_manager.clipboard = buff
		# print(buff)


class EGG_OT_export_to_path(bpy.types.Operator):
	'Export selected actions from list to separate .egg files with path'
	bl_idname = 'actions_to_egg.export'
	bl_label = 'Batch .egg animation export'

	@classmethod
	def poll(cls, context):
		try:
			return len(context.object.actions_to_egg.animations) > 0 and context.object.actions_to_egg.animations_path
		except:
			return False
		return True

	def execute(self, context):
		# ob = context.object.actions_to_egg
		ob = context.active_object
		context.window.cursor_set('WAIT')
		for animation_item in context.object.actions_to_egg.animations:
			if animation_item.select:
				egg_file_path = path.normpath(path.join(context.object.actions_to_egg.animations_path, animation_item.export_name + '.egg'))
				self.report({'INFO'}, 'Export action "{}" to file "{}"'.format(animation_item.name, egg_file_path))
				# try to cancel old animation
				try:
					bpy.ops.screen.animation_cancel()
				except:
					pass
				try:
					act = bpy.data.actions[animation_item.name]
				except:
					self.report({'WARNING'}, 'Export: action not found: "{}"'.format(animation_item.name))
				else:
					if not ob.animation_data:
						ob.animation_data_create()
					ob.animation_data.action = act
					# export action to .egg animation
					# todo: check the file path to destination path bound
					export_action_to_egg_file(act, ob, egg_file_path)

		context.window.cursor_set('DEFAULT')

		return {'FINISHED'}


class EGG_PT_egg_animations_export(View3DPanel, bpy.types.Panel):
	'Contains export animations list'
	bl_label = 'Animation to .egg export'
	bl_category = 'Animation'

	def draw(self, context):
		layout = self.layout

		row = layout.row(align=True)
		row.operator(operator='actions_to_egg.add_current_action')
		row.operator(operator='actions_to_egg.animations_popup_menu', text='', icon='COLLAPSEMENU')
		row.operator(operator='actions_to_egg.remove_action', text='', icon='X')
		try:
			layout.template_list(listtype_name='EGG_UL_animation_list_item', list_id='compact',
				dataptr=context.object.actions_to_egg, propname='animations',
				active_dataptr=context.object.actions_to_egg, active_propname='animations_index', rows=3)
		except:
			pass
		row = layout.row(align=True)
		try:
			row.prop(context.object.actions_to_egg, 'animations_path', text='')
		except:
			pass
		row.operator(operator='actions_to_egg.export', text='Export')


class EGG_animation_list_item(bpy.types.PropertyGroup):
	'Animation to export item'
	select: bpy.props.BoolProperty(name='Select', description='Whether to export the action')
	name: bpy.props.StringProperty(name='Name', description='Blender action name')
	export_name: bpy.props.StringProperty(name='ExportName', description='Panda3D animation name')


class EGG_UL_animation_list_item(bpy.types.UIList):

	def draw_item(self, _context, layout, _data, item: EGG_animation_list_item, _icon, _active_data, _active_propname):
		row = layout.row(align=True)
		row.prop(item, 'select', text='')
		row.label(text=item.name)
		row.prop(item, 'export_name', text='')


def animations_index_changed(self, context):
	'Selected animation changed in export table'
	# try to cancel & unlink old animation
	try:
		bpy.ops.screen.animation_cancel()
	except:
		pass
	try:
		# it can happened that unlink action is inaccessible
		bpy.ops.action.unlink()
	except:
		pass

	# play selected action
	# bpy.data.armatures[0].pose_position='POSE'
	animation_name = context.object.actions_to_egg.animations[context.object.actions_to_egg.animations_index].name
	try:
		# get new animation name
		act = bpy.data.actions[animation_name]
		ob = context.active_object
		if not ob.animation_data:
			ob.animation_data_create()
		ob.animation_data.action = act
	except Exception as e:
		pass
	else:
		# play an action from first to last frames in cycle
		try:
			# active_scene = bpy.context.window.scene # 2.80
			context.scene.frame_start = act.frame_range[0]
			context.scene.frame_current = act.frame_range[0]
			context.scene.frame_end = act.frame_range[1]
			bpy.ops.screen.animation_play()
		except:
			pass


class EGG_object_properties(bpy.types.PropertyGroup):
	animations: bpy.props.CollectionProperty(type=EGG_animation_list_item)
	animations_index: bpy.props.IntProperty(update=animations_index_changed)
	animations_path: bpy.props.StringProperty(subtype='DIR_PATH', description='Path to export .egg files')


classes = (
	EGG_animation_list_item,
	EGG_object_properties,
	EGG_PT_egg_animations_export,
	EGG_UL_animation_list_item,
	EGG_OT_add_animation,
	EGG_OT_remove_animation,
	EGG_OT_export_to_path,
	# actions popup menu
	EGG_OT_add_all_actions,
	EGG_OT_clear_animations_list,
	EGG_OT_animations_popup_menu,
	EGG_OT_deselect_all_animations,
	EGG_OT_invert_select_animations,
)

def register():
	for _ in classes:
		register_class(_)
	bpy.types.Object.actions_to_egg = bpy.props.PointerProperty(type=EGG_object_properties)

def unregister():
	for _ in reversed(classes):
		unregister_class(_)
	del bpy.types.Object.actions_to_egg

if __name__ == '__main__':
	register()
